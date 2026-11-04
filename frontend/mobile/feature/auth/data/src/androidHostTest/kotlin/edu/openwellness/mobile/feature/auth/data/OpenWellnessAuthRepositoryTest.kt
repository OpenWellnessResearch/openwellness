package edu.openwellness.mobile.feature.auth.data

import assertk.assertThat
import assertk.assertions.isEqualTo
import assertk.assertions.isNull
import edu.openwellness.mobile.core.data.auth.AuthTokenStorage
import edu.openwellness.mobile.core.data.network.ApiConfig
import edu.openwellness.mobile.core.domain.util.Result
import edu.openwellness.mobile.feature.auth.domain.AuthError
import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.HttpRequestData
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.headersOf
import io.ktor.serialization.kotlinx.json.json
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertTrue

private const val TOKEN_JSON =
    """{"accessToken":"access-1","tokenType":"Bearer","expiresInSeconds":900,"refreshToken":"refresh-1","principal":{"userId":"u1","participant":"participants/42"}}"""
private const val STAFF_TOKEN_JSON =
    """{"accessToken":"access-1","tokenType":"Bearer","expiresInSeconds":900,"refreshToken":"refresh-1","principal":{"userId":"u1","participant":null}}"""
private const val BLANK_PARTICIPANT_TOKEN_JSON =
    """{"accessToken":"access-1","tokenType":"Bearer","expiresInSeconds":900,"refreshToken":"refresh-1","principal":{"userId":"u1","participant":""}}"""
private const val REFRESH_JSON =
    """{"accessToken":"access-2","tokenType":"Bearer","expiresInSeconds":900,"refreshToken":"refresh-2"}"""
private const val ERROR_400_JSON =
    """{"error":{"code":400,"status":"INVALID_ARGUMENT","message":"The code is invalid or has expired.","details":[]}}"""
private const val ERROR_401_JSON =
    """{"error":{"code":401,"status":"UNAUTHENTICATED","message":"Authentication required."}}"""
private const val ERROR_429_WITH_SECS =
    """{"error":{"code":429,"status":"RESOURCE_EXHAUSTED","message":"Slow down.","details":[{"retry_after_secs":42}]}}"""
private const val ERROR_429_NO_SECS =
    """{"error":{"code":429,"status":"RESOURCE_EXHAUSTED","message":"Slow down.","details":[]}}"""

internal class FakeTokenStorage(
    initialAccess: String? = null,
    initialRefresh: String? = null,
) : AuthTokenStorage {
    private var access: String? = initialAccess
    private var refresh: String? = initialRefresh
    override suspend fun getAccessToken() = access
    override suspend fun getRefreshToken() = refresh
    override suspend fun saveTokens(accessToken: String, refreshToken: String) {
        access = accessToken
        refresh = refreshToken
    }
    override suspend fun clear() {
        access = null
        refresh = null
    }
}

class OpenWellnessAuthRepositoryTest {

    private fun buildRepo(
        storage: AuthTokenStorage,
        status: HttpStatusCode,
        body: String,
        retryAfterHeader: String? = null,
        onRequest: (HttpRequestData) -> Unit = {},
    ): OpenWellnessAuthRepository {
        val engine = MockEngine { request ->
            onRequest(request)
            val headers = if (retryAfterHeader != null) {
                headersOf(
                    HttpHeaders.ContentType to listOf("application/json"),
                    HttpHeaders.RetryAfter to listOf(retryAfterHeader),
                )
            } else {
                headersOf(HttpHeaders.ContentType, "application/json")
            }
            respond(content = body, status = status, headers = headers)
        }
        val client = HttpClient(engine) {
            install(ContentNegotiation) {
                json(Json { ignoreUnknownKeys = true; explicitNulls = false })
            }
        }
        val config = ApiConfig(baseUrl = "http://test.local/v1/", debug = false)
        return OpenWellnessAuthRepository(
            remote = KtorAuthRemoteDataSource(client, config),
            tokenStorage = storage,
            httpClient = client,
        )
    }

    @Test
    fun verifyLogin_onSuccess_returnsSession_savesTokens_andResolvesColonRoute() = runTest {
        val storage = FakeTokenStorage()
        var capturedUrl: String? = null
        val repo = buildRepo(storage, HttpStatusCode.OK, TOKEN_JSON) {
            capturedUrl = it.url.toString()
        }

        val result = repo.verifyLoginCode("person@example.com", "123456")

        assertTrue(result is Result.Success)
        assertThat(result.data.tokens.accessToken).isEqualTo("access-1")
        assertThat(result.data.principal.participant).isEqualTo("participants/42")
        assertThat(storage.getAccessToken()).isEqualTo("access-1")
        assertThat(storage.getRefreshToken()).isEqualTo("refresh-1")
        // The literal ':' must survive as a path char, not be parsed as a scheme.
        assertThat(capturedUrl).isEqualTo("http://test.local/v1/auth:verifyLoginCode")
    }

    @Test
    fun verify_on400_mapsToInvalidOrExpiredCode() = runTest {
        val repo = buildRepo(FakeTokenStorage(), HttpStatusCode.BadRequest, ERROR_400_JSON)

        val result = repo.verifyLoginCode("person@example.com", "000000")

        assertTrue(result is Result.Error)
        assertThat(result.error).isEqualTo(AuthError.InvalidOrExpiredCode)
    }

    @Test
    fun send_on429_withBodySecs_mapsToRateLimitedWithBodyValue() = runTest {
        val repo = buildRepo(FakeTokenStorage(), HttpStatusCode.TooManyRequests, ERROR_429_WITH_SECS)

        val result = repo.sendLoginCode("person@example.com")

        assertTrue(result is Result.Error)
        assertThat(result.error).isEqualTo(AuthError.RateLimited(42))
    }

    @Test
    fun send_on429_withHeaderOnly_mapsToRateLimitedWithHeaderValue() = runTest {
        val repo = buildRepo(
            FakeTokenStorage(),
            HttpStatusCode.TooManyRequests,
            ERROR_429_NO_SECS,
            retryAfterHeader = "30",
        )

        val result = repo.sendLoginCode("person@example.com")

        assertTrue(result is Result.Error)
        assertThat(result.error).isEqualTo(AuthError.RateLimited(30))
    }

    @Test
    fun send_on429_withNeither_mapsToRateLimitedDefault60() = runTest {
        val repo = buildRepo(FakeTokenStorage(), HttpStatusCode.TooManyRequests, ERROR_429_NO_SECS)

        val result = repo.sendLoginCode("person@example.com")

        assertTrue(result is Result.Error)
        assertThat(result.error).isEqualTo(AuthError.RateLimited(60))
    }

    @Test
    fun refresh_onSuccess_persistsRotatedPair() = runTest {
        val storage = FakeTokenStorage(initialAccess = "access-1", initialRefresh = "refresh-1")
        val repo = buildRepo(storage, HttpStatusCode.OK, REFRESH_JSON)

        val result = repo.refresh()

        assertTrue(result is Result.Success)
        assertThat(storage.getAccessToken()).isEqualTo("access-2")
        assertThat(storage.getRefreshToken()).isEqualTo("refresh-2")
    }

    @Test
    fun refresh_on401_mapsToUnauthorized_andClearsStorage() = runTest {
        val storage = FakeTokenStorage(initialAccess = "access-1", initialRefresh = "refresh-1")
        val repo = buildRepo(storage, HttpStatusCode.Unauthorized, ERROR_401_JSON)

        val result = repo.refresh()

        assertTrue(result is Result.Error)
        assertThat(result.error).isEqualTo(AuthError.Unauthorized)
        assertThat(storage.getAccessToken()).isNull()
        assertThat(storage.getRefreshToken()).isNull()
    }

    @Test
    fun refresh_withNoStoredToken_returnsUnauthorized_withoutNetwork() = runTest {
        var called = false
        val repo = buildRepo(FakeTokenStorage(), HttpStatusCode.OK, REFRESH_JSON) { called = true }

        val result = repo.refresh()

        assertTrue(result is Result.Error)
        assertThat(result.error).isEqualTo(AuthError.Unauthorized)
        assertThat(called).isEqualTo(false)
    }

    @Test
    fun verifyLogin_nullParticipant_rejected_noTokensSaved() = runTest {
        val storage = FakeTokenStorage()
        val repo = buildRepo(storage, HttpStatusCode.OK, STAFF_TOKEN_JSON)

        val result = repo.verifyLoginCode("coach@example.com", "123456")

        assertTrue(result is Result.Error)
        assertThat(result.error).isEqualTo(AuthError.NotParticipant)
        assertThat(storage.getAccessToken()).isNull()
        assertThat(storage.getRefreshToken()).isNull()
    }

    @Test
    fun verifyLogin_nullParticipant_attemptsRevoke() = runTest {
        val urls = mutableListOf<String>()
        val repo = buildRepo(FakeTokenStorage(), HttpStatusCode.OK, STAFF_TOKEN_JSON) {
            urls += it.url.toString()
        }

        repo.verifyLoginCode("coach@example.com", "123456")

        assertThat(urls).isEqualTo(
            listOf(
                "http://test.local/v1/auth:verifyLoginCode",
                "http://test.local/v1/auth:revokeToken",
            ),
        )
    }

    @Test
    fun verifyRegistration_nullParticipant_rejected() = runTest {
        val storage = FakeTokenStorage()
        val repo = buildRepo(storage, HttpStatusCode.OK, STAFF_TOKEN_JSON)

        val result = repo.verifyRegistrationCode("coach@example.com", "123456")

        assertTrue(result is Result.Error)
        assertThat(result.error).isEqualTo(AuthError.NotParticipant)
        assertThat(storage.getAccessToken()).isNull()
        assertThat(storage.getRefreshToken()).isNull()
    }

    @Test
    fun verifyLogin_blankParticipant_rejected() = runTest {
        val storage = FakeTokenStorage()
        val repo = buildRepo(storage, HttpStatusCode.OK, BLANK_PARTICIPANT_TOKEN_JSON)

        val result = repo.verifyLoginCode("person@example.com", "123456")

        assertTrue(result is Result.Error)
        assertThat(result.error).isEqualTo(AuthError.NotParticipant)
        assertThat(storage.getAccessToken()).isNull()
    }
}

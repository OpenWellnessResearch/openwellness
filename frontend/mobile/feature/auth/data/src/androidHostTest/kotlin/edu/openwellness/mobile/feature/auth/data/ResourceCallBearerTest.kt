package edu.openwellness.mobile.feature.auth.data

import assertk.assertThat
import assertk.assertions.isEqualTo
import assertk.assertions.isNull
import edu.openwellness.mobile.core.data.auth.AuthTokenStorage
import edu.openwellness.mobile.core.data.network.ApiConfig
import edu.openwellness.mobile.core.data.network.HttpClientFactory
import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.client.request.HttpRequestData
import io.ktor.client.request.get
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.headersOf
import kotlinx.coroutines.test.runTest
import kotlin.test.Test

/**
 * D-11 mobile proof: the app has no resource-call code yet, so this exercises the
 * shared client on a non-auth path. The enforced API requires a bearer there.
 * Assertions are on the request the engine captured, not on the response.
 */
class ResourceCallBearerTest {

    private suspend fun captureGet(
        storage: AuthTokenStorage,
        path: String,
    ): HttpRequestData {
        var captured: HttpRequestData? = null
        val engine = MockEngine { request ->
            captured = request
            respond(
                content = "{}",
                status = HttpStatusCode.OK,
                headers = headersOf(HttpHeaders.ContentType, "application/json"),
            )
        }
        val client = HttpClientFactory.create(
            engine = engine,
            config = ApiConfig(baseUrl = "http://test.local/v1/", debug = false),
            tokenStorage = storage,
            refreshClient = HttpClient(MockEngine { respond("{}") }),
        )

        client.get(path)

        return checkNotNull(captured) { "engine saw no request" }
    }

    @Test
    fun get_onResourcePath_attachesBearerPreemptively() = runTest {
        val request = captureGet(FakeTokenStorage("access-1", "refresh-1"), "users/p-1/weights")

        assertThat(request.url.encodedPath.endsWith("users/p-1/weights")).isEqualTo(true)
        assertThat(request.headers[HttpHeaders.Authorization]).isEqualTo("Bearer access-1")
    }

    @Test
    fun get_withNoStoredToken_sendsNoAuthorizationHeader() = runTest {
        val request = captureGet(FakeTokenStorage(), "users/p-1/weights")

        assertThat(request.headers[HttpHeaders.Authorization]).isNull()
    }
}

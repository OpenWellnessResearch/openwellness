package edu.openwellness.mobile.feature.auth.data

import edu.openwellness.mobile.core.data.auth.AuthTokenStorage
import edu.openwellness.mobile.core.data.network.HttpClientFactory
import edu.openwellness.mobile.core.domain.util.DataError
import edu.openwellness.mobile.core.domain.util.EmptyResult
import edu.openwellness.mobile.core.domain.util.Result
import edu.openwellness.mobile.feature.auth.data.mapper.toAuthSession
import edu.openwellness.mobile.feature.auth.data.mapper.toSendCodeResult
import edu.openwellness.mobile.feature.auth.domain.AuthError
import edu.openwellness.mobile.feature.auth.domain.AuthRepository
import edu.openwellness.mobile.feature.auth.domain.model.AuthSession
import edu.openwellness.mobile.feature.auth.domain.model.SendCodeResult
import io.ktor.client.HttpClient

/**
 * Maps [AuthRemoteError] → [AuthError], and centralizes token side effects:
 * verify persists the issued pair; refresh persists the ROTATED pair; revoke
 * clears storage. After any storage write/clear it invalidates the Ktor bearer
 * cache so the next authenticated request re-reads storage.
 */
internal class OpenWellnessAuthRepository(
    private val remote: KtorAuthRemoteDataSource,
    private val tokenStorage: AuthTokenStorage,
    private val httpClient: HttpClient,
) : AuthRepository {

    override suspend fun sendLoginCode(
        email: String,
    ): Result<SendCodeResult, AuthError> =
        when (val r = remote.sendLoginCode(email)) {
            is Result.Success -> Result.Success(r.data.toSendCodeResult())
            is Result.Error -> Result.Error(r.error.toAuthError())
        }

    override suspend fun sendRegistrationCode(
        email: String,
        participant: String,
    ): Result<SendCodeResult, AuthError> =
        when (val r = remote.sendRegistrationCode(email, participant)) {
            is Result.Success -> Result.Success(r.data.toSendCodeResult())
            is Result.Error -> Result.Error(r.error.toAuthError())
        }

    override suspend fun verifyLoginCode(
        email: String,
        code: String,
    ): Result<AuthSession, AuthError> =
        persistVerified(remote.verifyLoginCode(email, code))

    override suspend fun verifyRegistrationCode(
        email: String,
        code: String,
    ): Result<AuthSession, AuthError> =
        persistVerified(remote.verifyRegistrationCode(email, code))

    override suspend fun refresh(): EmptyResult<AuthError> {
        val storedRefresh = tokenStorage.getRefreshToken()
            ?: return Result.Error(AuthError.Unauthorized)

        return when (val r = remote.refresh(storedRefresh)) {
            is Result.Success -> {
                // Persist the ROTATED pair before returning — a stale stored
                // refresh would be a hard logout on next use.
                tokenStorage.saveTokens(r.data.accessToken, r.data.refreshToken)
                invalidateBearerCache()
                Result.Success(Unit)
            }
            is Result.Error -> {
                val authError = r.error.toAuthError()
                // A rejected refresh token means the session family is dead —
                // clear it so the app drops to an unauthenticated state.
                if (authError == AuthError.Unauthorized) {
                    clearSession()
                }
                Result.Error(authError)
            }
        }
    }

    override suspend fun revokeCurrent(): EmptyResult<AuthError> {
        val storedRefresh = tokenStorage.getRefreshToken()
        val outcome = storedRefresh?.let { remote.revokeCurrent(it) }
        clearSession()
        return outcome.toEmptyResult()
    }

    override suspend fun revokeAll(): EmptyResult<AuthError> {
        val outcome = remote.revokeAll()
        clearSession()
        return outcome.toEmptyResult()
    }

    private suspend fun persistVerified(
        result: Result<edu.openwellness.mobile.feature.auth.data.dto.TokenResponseDto, AuthRemoteError>,
    ): Result<AuthSession, AuthError> = when (result) {
        is Result.Success -> {
            val session = result.data.toAuthSession()
            if (session.principal.participant.isNullOrBlank()) {
                // UX gate only (the API is the security boundary). It runs before
                // the save so a staff token never reaches disk; the revoke is
                // best-effort so no live server session is left behind.
                remote.revokeCurrent(session.tokens.refreshToken)
                Result.Error(AuthError.NotParticipant)
            } else {
                tokenStorage.saveTokens(
                    session.tokens.accessToken,
                    session.tokens.refreshToken,
                )
                invalidateBearerCache()
                Result.Success(session)
            }
        }
        is Result.Error -> Result.Error(result.error.toAuthError())
    }

    private suspend fun clearSession() {
        tokenStorage.clear()
        invalidateBearerCache()
    }

    private fun invalidateBearerCache() {
        HttpClientFactory.clearBearerCache(httpClient)
    }

    /** Logout is locally authoritative — null (no stored token) is success. */
    private fun Result<*, AuthRemoteError>?.toEmptyResult(): EmptyResult<AuthError> =
        when (this) {
            null, is Result.Success -> Result.Success(Unit)
            is Result.Error -> Result.Error(error.toAuthError())
        }
}

internal fun AuthRemoteError.toAuthError(): AuthError = when (network) {
    DataError.Network.BAD_REQUEST -> AuthError.InvalidOrExpiredCode
    DataError.Network.TOO_MANY_REQUESTS ->
        AuthError.RateLimited(retryAfterSeconds ?: 60L)
    DataError.Network.UNAUTHORIZED -> AuthError.Unauthorized
    DataError.Network.NO_INTERNET -> AuthError.NoInternet
    DataError.Network.SERVER_ERROR,
    DataError.Network.SERVICE_UNAVAILABLE,
    -> AuthError.Server
    else -> AuthError.Unknown
}

package edu.openwellness.mobile.feature.auth.domain

import edu.openwellness.mobile.core.domain.util.Error

/**
 * Typed auth-domain failures.
 *
 * Verify failures surface uniformly as [InvalidOrExpiredCode] (the backend
 * returns an identical 400 for wrong/expired/missing codes — anti-enumeration).
 * [RateLimited] carries the authoritative server cooldown. The trailing three
 * are client-side validation failures produced before any network call.
 * [NotParticipant]: the account authenticated but has no participant, so this
 * app cannot serve it (e.g. a coach); the session is refused, never stored.
 */
sealed interface AuthError : Error {
    data object InvalidOrExpiredCode : AuthError
    data class RateLimited(val retryAfterSeconds: Long) : AuthError
    data object Unauthorized : AuthError
    data object NotParticipant : AuthError
    data object NoInternet : AuthError
    data object Server : AuthError
    data object Unknown : AuthError

    // Client-side validation failures.
    data object InvalidEmail : AuthError
    data object InvalidCode : AuthError
    data object EmptyParticipant : AuthError
}

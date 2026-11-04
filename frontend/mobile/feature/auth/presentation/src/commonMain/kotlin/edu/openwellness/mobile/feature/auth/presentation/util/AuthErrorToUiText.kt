package edu.openwellness.mobile.feature.auth.presentation.util

import edu.openwellness.mobile.core.presentation.util.UiText
import edu.openwellness.mobile.feature.auth.domain.AuthError
import edu.openwellness.mobile.feature.auth.presentation.resources.Res
import edu.openwellness.mobile.feature.auth.presentation.resources.auth_error_empty_participant
import edu.openwellness.mobile.feature.auth.presentation.resources.auth_error_invalid_code
import edu.openwellness.mobile.feature.auth.presentation.resources.auth_error_invalid_code_format
import edu.openwellness.mobile.feature.auth.presentation.resources.auth_error_invalid_email
import edu.openwellness.mobile.feature.auth.presentation.resources.auth_error_no_internet
import edu.openwellness.mobile.feature.auth.presentation.resources.auth_error_not_participant
import edu.openwellness.mobile.feature.auth.presentation.resources.auth_error_rate_limited
import edu.openwellness.mobile.feature.auth.presentation.resources.auth_error_server
import edu.openwellness.mobile.feature.auth.presentation.resources.auth_error_unauthorized
import edu.openwellness.mobile.feature.auth.presentation.resources.auth_error_unknown

fun AuthError.toUiText(): UiText {
    val resource = when (this) {
        AuthError.InvalidOrExpiredCode -> Res.string.auth_error_invalid_code
        is AuthError.RateLimited -> Res.string.auth_error_rate_limited
        AuthError.Unauthorized -> Res.string.auth_error_unauthorized
        AuthError.NotParticipant -> Res.string.auth_error_not_participant
        AuthError.NoInternet -> Res.string.auth_error_no_internet
        AuthError.Server -> Res.string.auth_error_server
        AuthError.Unknown -> Res.string.auth_error_unknown
        AuthError.InvalidEmail -> Res.string.auth_error_invalid_email
        AuthError.InvalidCode -> Res.string.auth_error_invalid_code_format
        AuthError.EmptyParticipant -> Res.string.auth_error_empty_participant
    }
    return UiText.StringResourceText(resource)
}

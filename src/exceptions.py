"""Exception types used across AutoPilot.

Keeping them in one place means callers can catch `AutoPilotError` for
"something in our automation went wrong" without also swallowing every
raw Selenium exception.
"""


class AutoPilotError(Exception):
    """Base class for every error AutoPilot raises on purpose."""


class UnsafeTargetError(AutoPilotError):
    """Raised when a URL outside the allow-list is requested.

    This is the ethical guardrail: the bot only drives sites that
    explicitly permit automation (see config.ALLOWED_HOSTS).
    """


class ElementNotReadyError(AutoPilotError):
    """An element never reached the state we waited for."""


class LoginFailedError(AutoPilotError):
    """The sandbox login did not produce a success banner."""


class DriverSetupError(AutoPilotError):
    """The browser/driver could not be started."""

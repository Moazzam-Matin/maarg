class MaargTrackingError(Exception):
    """Raised when maarg fails to persist a successful run in strict mode."""


class MaargTrackingWarning(UserWarning):
    """Warning emitted when maarg fails to persist tracking data."""
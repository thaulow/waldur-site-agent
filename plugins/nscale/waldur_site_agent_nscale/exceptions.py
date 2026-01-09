"""Custom exceptions for Nscale plugin."""


class NscaleError(Exception):
    """Base exception for Nscale-related errors."""


class NscaleAPIError(NscaleError):
    """Exception raised when Nscale API requests fail."""

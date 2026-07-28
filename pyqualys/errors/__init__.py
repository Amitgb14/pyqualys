# -*- coding: utf-8 -*-
"""
Exception hierarchy for pyqualys.

Nothing in this module ever embeds credentials or the full platform host
URL in a message - these exceptions travel to logs and to MCP clients.
"""

MAX_BODY_LENGTH = 512


class QualysError(Exception):
    """Base class for every error raised by pyqualys."""


class ParameterError(QualysError, ValueError):
    """
    Raised when the caller supplied an invalid combination of parameters.

    Also subclasses ValueError so that existing callers wrapping pyqualys
    in a generic ``except ValueError`` keep working.
    """


class QualysAPIError(QualysError):
    """
    Raised when the Qualys platform answered with an HTTP error status.

    :param message: human readable description, credential free.
    :param status_code: the HTTP status code returned by Qualys.
    :param body: the (truncated) response body, for debugging.
    """

    def __init__(self, message, status_code=None, body=None):
        self.status_code = status_code
        self.body = _truncate(body)
        super(QualysAPIError, self).__init__(message)


class RateLimitError(QualysAPIError):
    """
    Raised on HTTP 409 - Qualys signals rate and concurrency limits with
    409, not 429.

    :param retry_after: seconds to wait, parsed from the response header
                        ``X-RateLimit-ToWait-Sec`` when present.
    """

    def __init__(self, message, status_code=None, body=None,
                 retry_after=None):
        self.retry_after = retry_after
        super(RateLimitError, self).__init__(message,
                                             status_code=status_code,
                                             body=body)


def _truncate(body):
    """Return at most MAX_BODY_LENGTH characters of ``body``."""
    if body is None:
        return None
    body = body if isinstance(body, str) else str(body)
    if len(body) > MAX_BODY_LENGTH:
        return body[:MAX_BODY_LENGTH] + "..."
    return body

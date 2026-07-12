from __future__ import annotations


class QRStudioError(Exception):
    """Base exception for QR Studio application."""


class InvalidInputError(QRStudioError):
    """Raised when user input fails validation."""


class QRGenerationError(QRStudioError):
    """Raised when QR code generation fails unexpectedly."""

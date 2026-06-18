import logging

from app.core.config import settings

_logger = logging.getLogger("iam.email")


class EmailService:
    """
    Notification facade for transactional emails.
    In production swap the body of `send_password_reset` for any
    SMTP / SES / SendGrid call without touching callers.
    """

    async def send_password_reset(self, to_email: str, raw_token: str) -> None:
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        # Development / CI: emit the link to the iam.email logger so it is
        # visible in stdout without requiring a live SMTP server.
        _logger.info(
            "Password reset link dispatched",
            extra={"email": to_email, "reset_url": reset_url},
        )

"""Outbound email for security notifications (stdlib smtplib).

SMTP is optional: when SMTP_HOST is unset the message is logged instead of
sent, so local development never fails. Production must configure SMTP.
"""

import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_email(to_address, subject, body):
    """Send a plain-text email. Returns True when sent, False when skipped/failed."""
    from app.config import get_settings

    settings = get_settings()
    if not settings.SMTP_HOST or not to_address:
        logger.info(
            "SMTP not configured; skipping email to %s (subject: %s)",
            to_address, subject,
        )
        return False
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as client:
            if settings.SMTP_USE_TLS:
                client.starttls()
            if settings.SMTP_USER:
                client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            client.send_message(message)
        logger.info("Security email sent to %s", to_address)
        return True
    except Exception as exc:
        logger.warning("Could not send email to %s: %s", to_address, exc)
        return False

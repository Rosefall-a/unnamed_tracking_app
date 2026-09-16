from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from src.core.crypto import decrypt_secret
from src.database.models.app_integration_settings import AppIntegrationSettings


def send_email(settings: AppIntegrationSettings, recipient: str, subject: str, body: str) -> None:
    if not settings.smtp_enabled or not settings.smtp_host or not settings.smtp_from_email:
        raise RuntimeError("SMTP email is not configured.")

    password = decrypt_secret(settings.smtp_password) if settings.smtp_password else None
    message = EmailMessage()
    message["From"] = formataddr((settings.smtp_from_name or "Archive", settings.smtp_from_email))
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    smtp_cls = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
    with smtp_cls(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls and not settings.smtp_use_ssl:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, password or "")
        server.send_message(message)

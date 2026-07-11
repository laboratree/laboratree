"""Outbound messaging — a pluggable ``Mailer`` behind settings (like BlobStore/OCREngine).

Backends: ``console`` (default — logs instead of sending; dev/tests), ``smtp`` (any provider's
SMTP endpoint, incl. Resend/SES/SendGrid). Sending is per-message fail-soft: a delivery failure is
logged and reported in the result, never raised through a request.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from typing import Protocol

from ..config import settings

log = logging.getLogger(__name__)


@dataclass
class SendResult:
    to: str
    ok: bool
    error: str = ""


class Mailer(Protocol):
    def send(self, to: str, subject: str, html: str) -> SendResult: ...


@dataclass
class ConsoleMailer:
    """Dev/test backend: records + logs messages instead of delivering them."""

    sent: list[dict[str, str]] = field(default_factory=list)

    def send(self, to: str, subject: str, html: str) -> SendResult:
        self.sent.append({"to": to, "subject": subject, "html": html})
        log.info("console mailer: to=%s subject=%r (%d chars)", to, subject, len(html))
        return SendResult(to=to, ok=True)


class SmtpMailer:
    """Plain SMTP backend (works with Resend/SES/SendGrid SMTP endpoints)."""

    def send(self, to: str, subject: str, html: str) -> SendResult:
        msg = MIMEText(html, "html")
        msg["Subject"] = subject
        msg["From"] = settings.mail_from
        msg["To"] = to
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.sendmail(settings.mail_from, [to], msg.as_string())
            return SendResult(to=to, ok=True)
        except (smtplib.SMTPException, OSError) as exc:
            log.warning("smtp send to %s failed: %s", to, exc)
            return SendResult(to=to, ok=False, error=str(exc))


_mailer: Mailer | None = None


def get_mailer() -> Mailer:
    global _mailer
    if _mailer is None:
        provider = settings.mail_provider.lower()
        _mailer = SmtpMailer() if provider == "smtp" else ConsoleMailer()
        log.info("mailer initialised: %s", provider)
    return _mailer


def reset_mailer() -> None:
    """Test hook: force re-initialisation (e.g. after monkeypatching settings)."""
    global _mailer
    _mailer = None


__all__ = ["Mailer", "ConsoleMailer", "SmtpMailer", "SendResult", "get_mailer", "reset_mailer"]

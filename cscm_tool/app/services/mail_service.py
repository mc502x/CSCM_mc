"""Optional e-mail through the organisation's own SMTP relay (I-08, decision D-04).

Mail is off unless `SMTP_HOST` is configured; the application never talks to an
external mail provider (docs/11-security-architecture.md §12). A failure to send
is logged and reported to the caller but never breaks the workflow action that
triggered it."""

import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

log = logging.getLogger("cscm")


class MailService:
    @staticmethod
    def enabled() -> bool:
        return bool(current_app.config.get("SMTP_HOST"))

    @staticmethod
    def send(to_address: str, subject: str, body: str) -> bool:
        if not MailService.enabled():
            return False
        cfg = current_app.config
        message = EmailMessage()
        message["From"] = cfg["SMTP_SENDER"]
        message["To"] = to_address
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=10) as smtp:
                if cfg.get("SMTP_STARTTLS"):
                    smtp.starttls()
                if cfg.get("SMTP_USERNAME"):
                    smtp.login(cfg["SMTP_USERNAME"], cfg.get("SMTP_PASSWORD") or "")
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException):
            log.warning("could not send mail to %s", to_address, exc_info=True)
            return False
        return True

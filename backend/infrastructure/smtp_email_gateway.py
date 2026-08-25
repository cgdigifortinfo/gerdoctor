"""SMTP delivery adapter for email notifications."""
from __future__ import annotations

import asyncio
import logging
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from slices.email_notifications.models import DeliveryResult

logger = logging.getLogger("server")


class SmtpEmailGateway:
    def __init__(self, host: str, port: int, username: str, password: str,
                 from_email: str, from_name: str = "IHCA") -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_email = from_email
        self._from_name = from_name

    def send_sync(self, recipient: str, subject: str, html: str) -> DeliveryResult:
        if not self._username or not self._from_email:
            logger.info("Email not configured. Would send to %s: %s", recipient, subject)
            return DeliveryResult("skipped", message="Email not configured")
        try:
            message = MIMEMultipart("alternative")
            message["From"] = formataddr((self._from_name, self._from_email))
            message["To"] = recipient
            message["Subject"] = subject
            message.attach(MIMEText(html, "html"))
            with smtplib.SMTP(self._host, self._port, timeout=10) as server:
                server.starttls()
                server.login(self._username, self._password)
                server.send_message(message)
            return DeliveryResult("success")
        except (smtplib.SMTPException, ConnectionRefusedError, socket.gaierror, TimeoutError) as error:
            logger.error("SMTP error sending to %s: %s", recipient, error)
            return DeliveryResult("failed", error=str(error))
        except Exception as error:
            logger.error("Failed to send email to %s: %s", recipient, error)
            return DeliveryResult("failed", error=str(error))

    async def send(self, recipient: str, subject: str, html: str) -> DeliveryResult:
        return await asyncio.to_thread(self.send_sync, recipient, subject, html)

"""Simple SMTP mail sender for password reset emails."""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER or "no-reply@safedata.local")


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = "Recuperación de contraseña — SafeData Intelligence"
    msg["From"] = MAIL_FROM
    msg["To"] = to_email
    html = f"""
    <html><body>
      <p>Has solicitado restablecer tu contraseña.</p>
      <p>
        Haz clic en el siguiente enlace (válido por 24 horas):<br/>
        <a href="{reset_url}">{reset_url}</a>
      </p>
      <p>Si no solicitaste este cambio, ignora este correo.</p>
    </body></html>
    """
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


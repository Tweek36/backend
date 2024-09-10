from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import aiosmtplib
from app.config import settings


async def send_email(to_email: str, subject: str, body: str):
    message = MIMEMultipart()
    message["From"] = settings.EMAIL_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    async with aiosmtplib.SMTP(
        hostname=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        use_tls=settings.EMAIL_USE_TLS,
        username=settings.EMAIL_FROM,
        password=settings.EMAIL_PASSWORD,
    ) as smtp:
        await smtp.send_message(message)

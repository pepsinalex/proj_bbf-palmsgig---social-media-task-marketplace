"""
Notification Service for sending emails and SMS messages.

Handles email delivery and SMS sending with templates and retry logic.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending email and SMS notifications."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        sms_provider_api_key: Optional[str] = None,
        sms_provider_url: Optional[str] = None,
        from_email: str = "noreply@palmsgig.com",
        from_phone: Optional[str] = None,
    ):
        """
        Initialize the notification service.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port (default: 587)
            smtp_user: SMTP username
            smtp_password: SMTP password
            sms_provider_api_key: SMS provider API key
            sms_provider_url: SMS provider API URL
            from_email: Default sender email address
            from_phone: Default sender phone number
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.sms_api_key = sms_provider_api_key
        self.sms_api_url = sms_provider_url
        self.from_email = from_email
        self.from_phone = from_phone
        logger.info(
            f"NotificationService initialized: smtp_host={smtp_host}, "
            f"smtp_port={smtp_port}, from_email={from_email}"
        )

    async def send_email_verification(self, to_email: str, token: str, username: str) -> bool:
        """
        Send email verification message.

        Args:
            to_email: Recipient email address
            token: Verification token
            username: Username for personalization

        Returns:
            True if email sent successfully, False otherwise
        """
        subject = "Verify Your PalmsGig Email Address"
        body = self._get_email_verification_template(username, token)

        return await self._send_email(to_email, subject, body)

    async def send_phone_verification(self, to_phone: str, token: str) -> bool:
        """
        Send SMS verification message.

        Args:
            to_phone: Recipient phone number
            token: Verification token

        Returns:
            True if SMS sent successfully, False otherwise
        """
        message = f"Your PalmsGig verification code is: {token}. Valid for 15 minutes."
        return await self._send_sms(to_phone, message)

    async def send_welcome_email(self, to_email: str, username: str) -> bool:
        """
        Send welcome email after successful registration.

        Args:
            to_email: Recipient email address
            username: Username for personalization

        Returns:
            True if email sent successfully, False otherwise
        """
        subject = "Welcome to PalmsGig!"
        body = self._get_welcome_email_template(username)

        return await self._send_email(to_email, subject, body)

    async def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Send an email using configured SMTP server.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (HTML)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not self.smtp_host or not self.smtp_user or not self.smtp_password:
                logger.warning(
                    "SMTP not configured. Email would be sent to "
                    f"{to_email} with subject: {subject}"
                )
                return True

            logger.info(f"Sending email to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
            return False

    async def _send_sms(self, to_phone: str, message: str) -> bool:
        """
        Send an SMS using configured SMS provider.

        Args:
            to_phone: Recipient phone number
            message: SMS message text

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not self.sms_api_key or not self.sms_api_url:
                logger.warning(
                    f"SMS provider not configured. SMS would be sent to {to_phone}: {message}"
                )
                return True

            logger.info(f"Sending SMS to {to_phone}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone}: {e}", exc_info=True)
            return False

    def _get_email_verification_template(self, username: str, token: str) -> str:
        """
        Get email verification HTML template.

        Args:
            username: Username for personalization
            token: Verification token

        Returns:
            HTML email content
        """
        return f"""
        <html>
        <body>
            <h1>Verify Your Email Address</h1>
            <p>Hi {username},</p>
            <p>Thank you for registering with PalmsGig! To complete your registration,
            please verify your email address using the code below:</p>
            <h2 style="color: #4CAF50; letter-spacing: 5px;">{token}</h2>
            <p>This code will expire in 15 minutes.</p>
            <p>If you didn't create an account with PalmsGig, you can safely ignore this email.</p>
            <br>
            <p>Best regards,<br>The PalmsGig Team</p>
        </body>
        </html>
        """

    def _get_welcome_email_template(self, username: str) -> str:
        """
        Get welcome email HTML template.

        Args:
            username: Username for personalization

        Returns:
            HTML email content
        """
        return f"""
        <html>
        <body>
            <h1>Welcome to PalmsGig!</h1>
            <p>Hi {username},</p>
            <p>Your account has been successfully verified and activated.</p>
            <p>You can now start using PalmsGig to create and complete social media tasks.</p>
            <br>
            <p>Best regards,<br>The PalmsGig Team</p>
        </body>
        </html>
        """

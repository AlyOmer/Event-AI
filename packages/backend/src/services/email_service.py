"""
Email Service — SMTP-based email dispatch with fire-and-forget pattern.
Logs emails in dev mode when SMTP is not configured.
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from src.config.database import get_settings
import structlog

logger = structlog.get_logger()


class EmailService:
    """Fire-and-forget email dispatch — never blocks the caller."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._smtp_configured = bool(
            self._settings.smtp_host and self._settings.smtp_user
        )

    async def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """
        Send email via SMTP (fire-and-forget).
        Returns True if queued/sent, False if skipped.
        Errors are logged but never raised.
        """
        if not self._smtp_configured:
            # Dev mode: log email content instead of sending
            logger.info(
                "email.dev_mode",
                to=to,
                subject=subject,
                body_preview=body_text or body_html[:200] + "...",
            )
            return True

        # Fire-and-forget: spawn background task
        asyncio.create_task(
            self._send_smtp_email(
                to=to,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                from_email=from_email,
                reply_to=reply_to,
            )
        )
        return True

    async def _send_smtp_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        max_retries: int = 3,
    ) -> bool:
        """Internal: send via SMTP with retry logic."""
        sender = from_email or self._settings.email_from

        for attempt in range(1, max_retries + 1):
            try:
                msg = MIMEMultipart("alternative")
                msg["From"] = sender
                msg["To"] = to
                msg["Subject"] = subject
                if reply_to:
                    msg["Reply-To"] = reply_to
                msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

                if body_text:
                    msg.attach(MIMEText(body_text, "plain"))
                msg.attach(MIMEText(body_html, "html"))

                # Connect and send
                with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port) as server:
                    if self._settings.smtp_secure:
                        server.starttls()
                    if self._settings.smtp_user and self._settings.smtp_password:
                        server.login(self._settings.smtp_user, self._settings.smtp_password)
                    server.sendmail(sender, to, msg.as_string())

                logger.info("email.sent", to=to, subject=subject, attempt=attempt)
                return True

            except Exception as e:
                logger.warning(
                    "email.send_failed",
                    to=to,
                    subject=subject,
                    attempt=attempt,
                    error=str(e),
                )
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)  # exponential backoff

        logger.error(
            "email.permanent_failure",
            to=to,
            subject=subject,
            attempts=max_retries,
        )
        return False

    def render_booking_email(
        self,
        event_type: str,
        vendor_name: str,
        event_date: str,
        event_name: str,
        **extra: Any,
    ) -> tuple[str, str]:
        """Render email subject and HTML body for booking events."""
        templates = {
            "booking.created": (
                "Booking Request Received",
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #2563eb;">Booking Request Received</h2>
                    <p>Your booking request has been submitted successfully.</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Vendor:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{vendor_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Event:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_date}</td></tr>
                    </table>
                    <p style="color: #666;">You will receive a confirmation once the vendor accepts your request.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">Event-AI — Pakistan's Event Planning Marketplace</p>
                </div>
                """,
            ),
            "booking.confirmed": (
                "Booking Confirmed ✓",
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #16a34a;">Booking Confirmed ✓</h2>
                    <p>Great news! Your booking has been confirmed.</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Vendor:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{vendor_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Event:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_date}</td></tr>
                    </table>
                    <p style="color: #666;">Contact the vendor for any additional details.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">Event-AI — Pakistan's Event Planning Marketplace</p>
                </div>
                """,
            ),
            "booking.cancelled": (
                "Booking Cancelled",
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #dc2626;">Booking Cancelled</h2>
                    <p>Your booking has been cancelled.</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Vendor:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{vendor_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Event:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_date}</td></tr>
                    </table>
                    <p style="color: #666;">If you have questions, please contact the vendor.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">Event-AI — Pakistan's Event Planning Marketplace</p>
                </div>
                """,
            ),
            "booking.rejected": (
                "Booking Request Declined",
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #dc2626;">Booking Request Declined</h2>
                    <p>Unfortunately, your booking request was declined by the vendor.</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Vendor:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{vendor_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Event:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_date}</td></tr>
                    </table>
                    <p style="color: #666;">You can search for alternative vendors on our platform.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">Event-AI — Pakistan's Event Planning Marketplace</p>
                </div>
                """,
            ),
            "booking.completed": (
                "Your Event is Complete — Leave a Review!",
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #2563eb;">Your Event is Complete! 🎉</h2>
                    <p>We hope you had a wonderful event!</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Vendor:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{vendor_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Event:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_date}</td></tr>
                    </table>
                    <p style="color: #666;">Help others by leaving a review for your vendor!</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">Event-AI — Pakistan's Event Planning Marketplace</p>
                </div>
                """,
            ),
            "new_booking_request": (
                "New Booking Request",
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #2563eb;">New Booking Request</h2>
                    <p>You have received a new booking request.</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Event:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_name}</td></tr>
                        <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{event_date}</td></tr>
                    </table>
                    <p style="color: #666;">Log in to your vendor portal to review and respond.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">Event-AI — Pakistan's Event Planning Marketplace</p>
                </div>
                """,
            ),
        }

        return templates.get(
            event_type,
            (f"Notification: {event_type}", f"<p>{event_name} - {event_date}</p>"),
        )


email_service = EmailService()

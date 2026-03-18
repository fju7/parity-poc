"""Parity Signal auth — OTP email with correct branding.

Uses Supabase Auth admin API to generate OTP codes, then sends
branded email via Resend. Frontend verification still uses
supabase.auth.verifyOtp() to create a native Supabase Auth session.

POST /api/signal/auth/send-otp  — generate OTP via Supabase, send branded email
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from routers.employer_shared import _get_supabase
from utils.email import send_email

router = APIRouter(prefix="/api/signal/auth", tags=["signal-auth"])

OTP_EXPIRY_MINUTES = 10


class SendOtpRequest(BaseModel):
    email: str


def _send_signal_otp_email(email: str, code: str):
    send_email(
        to=email,
        subject=f"Your Parity Signal sign-in code: {code}",
        from_name="Parity Signal",
        html=f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
          <h2 style="color: #0D7377;">Your sign-in code</h2>
          <p>Enter this code to sign in to Parity Signal:</p>
          <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #0D7377;
                       padding: 24px; background: #f0fdfa; border-radius: 8px; text-align: center;">
            {code}
          </div>
          <p style="color: #666; font-size: 14px; margin-top: 24px;">
            This code expires in {OTP_EXPIRY_MINUTES} minutes. If you didn't request this,
            you can safely ignore this email.
          </p>
          <p style="color: #999; font-size: 12px;">CivicScale &middot; civicscale.ai</p>
        </div>
        """,
    )


@router.post("/send-otp")
async def send_otp(req: SendOtpRequest):
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    sb = _get_supabase()

    # Use Supabase Admin API to generate a magic-link OTP without
    # Supabase sending its own (incorrectly branded) email.
    try:
        result = sb.auth.admin.generate_link({
            "type": "magiclink",
            "email": email,
        })
    except Exception as exc:
        print(f"[SignalAuth] generate_link failed for {email}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to generate sign-in code")

    otp_code = result.properties.email_otp
    if not otp_code:
        print(f"[SignalAuth] No email_otp in generate_link response for {email}")
        raise HTTPException(status_code=500, detail="Failed to generate sign-in code")

    _send_signal_otp_email(email, otp_code)

    return {"sent": True, "email": email}

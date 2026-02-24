# parity-poc
Parity-Medical

## Supabase SMTP Configuration

Before go-live, configure a custom SMTP provider in **Supabase Dashboard > Authentication > SMTP Settings** to replace the built-in email service. The free tier has strict rate limits that will block sign-up and magic-link emails in production.

Recommended providers: **Resend** or **SendGrid**.

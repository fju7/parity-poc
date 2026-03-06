import { useState, useRef, useEffect } from "react";
import { supabase } from "../lib/supabase.js";

/**
 * Shared 8-digit OTP code input for email sign-in.
 * Adapted from SignalLogin.jsx phone OTP pattern.
 *
 * Props:
 *   email    — the email address the code was sent to
 *   onBack   — callback to return to the email input step
 */
export default function EmailOtpInput({ email, onBack }) {
  const [otp, setOtp] = useState(["", "", "", "", "", "", "", ""]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [resendCountdown, setResendCountdown] = useState(60);
  const [resent, setResent] = useState(false);
  const otpRefs = useRef([]);

  // Countdown timer
  useEffect(() => {
    if (resendCountdown <= 0) return;
    const t = setTimeout(() => setResendCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCountdown]);

  // Focus first input on mount
  useEffect(() => {
    setTimeout(() => otpRefs.current[0]?.focus(), 50);
  }, []);

  function handleOtpChange(index, value) {
    const digit = value.replace(/\D/g, "").slice(-1);
    const next = [...otp];
    next[index] = digit;
    setOtp(next);

    if (digit && index < 7) {
      otpRefs.current[index + 1]?.focus();
    }

    if (next.every((d) => d)) {
      verifyOtp(next.join(""));
    }
  }

  function handleOtpKeyDown(index, e) {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
  }

  function handleOtpPaste(e) {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 8);
    if (!pasted) return;

    const next = [...otp];
    for (let i = 0; i < 8; i++) {
      next[i] = pasted[i] || "";
    }
    setOtp(next);

    const focusIdx = Math.min(pasted.length, 7);
    otpRefs.current[focusIdx]?.focus();

    if (pasted.length === 8) {
      verifyOtp(pasted);
    }
  }

  async function verifyOtp(code) {
    setSending(true);
    setError(null);

    const { error: verifyError } = await supabase.auth.verifyOtp({
      email,
      token: code,
      type: "email",
    });

    setSending(false);

    if (verifyError) {
      setError(verifyError.message);
      setOtp(["", "", "", "", "", "", "", ""]);
      otpRefs.current[0]?.focus();
    }
    // Success is handled by onAuthStateChange listener in the parent
  }

  async function handleResend() {
    if (resendCountdown > 0) return;
    setSending(true);
    setError(null);

    const { error: otpError } = await supabase.auth.signInWithOtp({
      email,
      // No emailRedirectTo — this makes Supabase send a code, not a link
    });

    setSending(false);

    if (otpError) {
      setError(otpError.message);
      return;
    }

    setResendCountdown(60);
    setOtp(["", "", "", "", "", "", "", ""]);
    setResent(true);
    setTimeout(() => setResent(false), 3000);
    otpRefs.current[0]?.focus();
  }

  return (
    <div className="text-center py-2">
      <p className="text-sm text-gray-600 mb-1">
        We sent an 8-digit code to <strong>{email}</strong>.
      </p>
      <p className="text-xs text-gray-400 mb-4">
        Check your inbox and enter it below. The code expires in 10 minutes.
      </p>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex justify-center gap-1.5 mb-4" onPaste={handleOtpPaste}>
        {otp.map((digit, i) => (
          <input
            key={i}
            ref={(el) => (otpRefs.current[i] = el)}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={digit}
            onChange={(e) => handleOtpChange(i, e.target.value)}
            onKeyDown={(e) => handleOtpKeyDown(i, e)}
            className="w-9 h-11 text-center text-base font-semibold border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377] transition"
          />
        ))}
      </div>

      {sending && (
        <p className="text-sm text-gray-400 text-center mb-3">Verifying...</p>
      )}

      {resent && !error && (
        <p className="text-sm text-[#0D7377] text-center mb-3">New code sent!</p>
      )}

      <div className="text-center text-sm">
        {resendCountdown > 0 ? (
          <span className="text-gray-400">
            Resend code in {resendCountdown}s
          </span>
        ) : (
          <button
            onClick={handleResend}
            disabled={sending}
            className="text-[#0D7377] hover:underline bg-transparent border-none cursor-pointer disabled:opacity-50"
          >
            {sending ? "Sending..." : "Resend code"}
          </button>
        )}
      </div>

      <div className="mt-4 text-center">
        <button
          onClick={onBack}
          className="text-xs text-gray-400 hover:text-gray-600 bg-transparent border-none cursor-pointer transition"
        >
          Use a different email
        </button>
      </div>
    </div>
  );
}

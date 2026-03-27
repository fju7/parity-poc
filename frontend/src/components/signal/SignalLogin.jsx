import { useState, useRef, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { supabase } from "../../lib/supabase";
import { API_BASE } from "../../lib/apiBase";
import EmailOtpInput from "../EmailOtpInput.jsx";

export default function SignalLogin({ signup = false }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const returnTo = searchParams.get("returnTo");

  // Flow state
  const [method, setMethod] = useState("email"); // phone | email
  const [step, setStep] = useState("input"); // input | code
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [resent, setResent] = useState(false);

  // Phone state
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [resendCountdown, setResendCountdown] = useState(0);
  const otpRefs = useRef([]);

  // Email state
  const [email, setEmail] = useState("");

  // Resend countdown timer
  useEffect(() => {
    if (resendCountdown <= 0) return;
    const t = setTimeout(() => setResendCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCountdown]);

  // Listen for auth state change (redirect on success)
  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) navigate(returnTo || "/signal", { replace: true });
    });
    return () => subscription.unsubscribe();
  }, [navigate, returnTo]);

  // ── Phone helpers ──

  function formatPhoneInput(value) {
    return value.replace(/\D/g, "").slice(0, 10);
  }

  function displayPhone(digits) {
    if (digits.length <= 3) return digits;
    if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }

  async function handleSendCode() {
    const digits = phone.replace(/\D/g, "");
    if (digits.length !== 10) {
      setError("Please enter a valid 10-digit US phone number.");
      return;
    }

    setSending(true);
    setError(null);

    const { error: otpError } = await supabase.auth.signInWithOtp({
      phone: "+1" + digits,
    });

    setSending(false);

    if (otpError) {
      setError(otpError.message);
      return;
    }

    setStep("code");
    setResendCountdown(60);
    // Focus first OTP input
    setTimeout(() => otpRefs.current[0]?.focus(), 50);
  }

  function handleOtpChange(index, value) {
    // Allow only digits
    const digit = value.replace(/\D/g, "").slice(-1);
    const next = [...otp];
    next[index] = digit;
    setOtp(next);

    // Auto-advance
    if (digit && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all 6 filled
    if (digit && index === 5 && next.every((d) => d)) {
      verifyOtp(next.join(""));
    } else if (next.every((d) => d)) {
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
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (!pasted) return;

    const next = [...otp];
    for (let i = 0; i < 6; i++) {
      next[i] = pasted[i] || "";
    }
    setOtp(next);

    // Focus last filled or next empty
    const focusIdx = Math.min(pasted.length, 5);
    otpRefs.current[focusIdx]?.focus();

    // Auto-submit if full
    if (pasted.length === 6) {
      verifyOtp(pasted);
    }
  }

  async function verifyOtp(code) {
    const digits = phone.replace(/\D/g, "");
    setSending(true);
    setError(null);

    const { error: verifyError } = await supabase.auth.verifyOtp({
      phone: "+1" + digits,
      token: code,
      type: "sms",
    });

    setSending(false);

    if (verifyError) {
      setError(verifyError.message);
      setOtp(["", "", "", "", "", ""]);
      otpRefs.current[0]?.focus();
    }
    // Success is handled by onAuthStateChange listener
  }

  async function handleResend() {
    if (resendCountdown > 0) return;
    const digits = phone.replace(/\D/g, "");
    setSending(true);
    setError(null);

    const { error: otpError } = await supabase.auth.signInWithOtp({
      phone: "+1" + digits,
    });

    setSending(false);

    if (otpError) {
      setError(otpError.message);
      return;
    }

    setResendCountdown(60);
    setOtp(["", "", "", "", "", ""]);
    setResent(true);
    setTimeout(() => setResent(false), 3000);
    otpRefs.current[0]?.focus();
  }

  // ── Email helpers ──

  async function sendSignalOtp(emailAddr) {
    const res = await fetch(`${API_BASE}/api/signal/auth/send-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: emailAddr.trim().toLowerCase() }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Failed to send code");
    }
  }

  async function handleSendEmailCode() {
    if (!email || !email.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }

    setSending(true);
    setError(null);

    try {
      await sendSignalOtp(email);
    } catch (err) {
      setError(err.message);
      setSending(false);
      return;
    }

    setSending(false);
    setStep("code");
  }

  // ── Render ──

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex items-center justify-center px-4 py-12 font-[Arial,sans-serif]">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-white mb-2">
            {signup ? "Start your free trial" : "Sign in to Parity Signal"}
          </h1>
          <p className="text-sm text-gray-300 leading-relaxed">
            {signup
              ? "Create your account to subscribe to topics, ask evidence questions, and access scored research."
              : "Subscribe to topics, ask evidence questions, and request new research."}
          </p>
        </div>

        {/* Tier info */}
        <div className="bg-gray-50 rounded-xl p-4 mb-6 text-center">
          <p className="text-xs font-semibold text-[#1B3A5C] mb-2">Free accounts include</p>
          <div className="flex justify-center gap-6 text-xs text-gray-500">
            <span>3 topics</span>
            <span className="text-gray-300">|</span>
            <span>5 questions/mo</span>
          </div>
          <Link
            to="/pricing"
            className="text-[10px] text-[#0D7377] hover:underline mt-2 inline-block no-underline"
          >
            View plans for more access &rarr;
          </Link>
        </div>

        {/* Card */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          {/* ── Phone: input step ── */}
          {method === "phone" && step === "input" && (
            <>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Phone number
              </label>
              <div className="flex items-center gap-2 mb-4">
                <span className="text-sm text-gray-400 select-none">+1</span>
                <input
                  type="tel"
                  inputMode="numeric"
                  placeholder="(555) 123-4567"
                  value={displayPhone(phone)}
                  onChange={(e) => setPhone(formatPhoneInput(e.target.value))}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSendCode();
                  }}
                  className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377] transition"
                  autoFocus
                />
              </div>

              <p className="text-[10px] text-gray-400 leading-snug mb-4">
                By entering your phone number, you consent to receive a one-time verification code via SMS from CivicScale. Message and data rates may apply. Message frequency: 1 per login attempt. Reply STOP to opt out. See our{" "}
                <a href="/privacy" className="underline hover:text-gray-500">Privacy Policy</a>.
              </p>

              <button
                onClick={handleSendCode}
                disabled={sending || phone.replace(/\D/g, "").length !== 10}
                className="w-full py-2.5 rounded-lg text-sm font-semibold text-white bg-[#0D7377] hover:bg-[#0B6265] disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {sending ? "Sending..." : "Send Code"}
              </button>

              <div className="mt-4 text-center">
                <button
                  onClick={() => {
                    setMethod("email");
                    setStep("input");
                    setError(null);
                  }}
                  className="text-xs text-gray-400 hover:text-gray-600 bg-transparent border-none cursor-pointer transition"
                >
                  Use email instead
                </button>
              </div>
            </>
          )}

          {/* ── Phone: code step ── */}
          {method === "phone" && step === "code" && (
            <>
              <p className="text-sm text-gray-600 mb-1">
                Enter the 6-digit code sent to
              </p>
              <p className="text-sm font-medium text-[#1B3A5C] mb-1">
                +1 {displayPhone(phone)}
              </p>
              <p className="text-xs text-gray-400 mb-4">
                May take up to 30 seconds. Check your messages app.
              </p>

              <div className="flex justify-center gap-2 mb-4" onPaste={handleOtpPaste}>
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
                    className="w-10 h-12 text-center text-lg font-semibold border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377] transition"
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
                  onClick={() => {
                    setStep("input");
                    setOtp(["", "", "", "", "", ""]);
                    setError(null);
                  }}
                  className="text-xs text-gray-400 hover:text-gray-600 bg-transparent border-none cursor-pointer transition"
                >
                  Change phone number
                </button>
              </div>
            </>
          )}

          {/* ── Email: input step ── */}
          {method === "email" && step === "input" && (
            <>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Email address
              </label>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSendEmailCode();
                }}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377] transition mb-4"
                autoFocus
              />

              <button
                onClick={handleSendEmailCode}
                disabled={sending || !email.includes("@")}
                className="w-full py-2.5 rounded-lg text-sm font-semibold text-white bg-[#0D7377] hover:bg-[#0B6265] disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {sending ? "Sending..." : "Send Code"}
              </button>

              <div className="mt-4 text-center">
                <button
                  onClick={() => {
                    setMethod("phone");
                    setStep("input");
                    setError(null);
                  }}
                  className="text-xs text-gray-400 hover:text-gray-600 bg-transparent border-none cursor-pointer transition"
                >
                  Use phone instead
                </button>
              </div>
            </>
          )}

          {/* ── Email: code entry ── */}
          {method === "email" && step === "code" && (
            <EmailOtpInput
              email={email}
              onBack={() => {
                setStep("input");
                setError(null);
              }}
              onResend={sendSignalOtp}
            />
          )}
        </div>

        {/* Back to Signal link */}
        <div className="mt-6 text-center">
          <Link
            to="/signal"
            className="text-sm text-gray-400 hover:text-gray-300 no-underline transition"
          >
            Back to Parity Signal
          </Link>
        </div>
      </div>
    </div>
  );
}

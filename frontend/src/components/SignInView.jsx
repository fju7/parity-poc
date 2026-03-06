import { useState, useCallback } from "react";
import { supabase } from "../lib/supabase.js";
import { getRedirectOrigin } from "../lib/redirectOrigin.js";
import { Footer } from "./UploadView.jsx";

export default function SignInView() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("idle"); // idle | sending | sent | error
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      setStatus("sending");
      setErrorMsg("");

      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: getRedirectOrigin() + "/parity-health/" },
      });

      if (error) {
        setStatus("error");
        setErrorMsg(error.message);
      } else {
        setStatus("sent");
      }
    },
    [email]
  );

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-4 font-[Arial,sans-serif]">
      <div className="w-full max-w-sm text-center">
        {/* Logo */}
        <h1 className="text-5xl font-bold text-[#1B3A5C] mb-2 tracking-tight">
          Parity Health
        </h1>
        <p className="text-lg text-gray-500 mb-10">Bill Analysis</p>

        {status === "sent" ? (
          <div className="bg-[#0D7377]/5 border border-[#0D7377]/20 rounded-xl p-6">
            <svg
              className="w-10 h-10 text-[#0D7377] mx-auto mb-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75"
              />
            </svg>
            <p className="text-[#1B3A5C] font-semibold mb-1">
              Check your email
            </p>
            <p className="text-sm text-gray-500">
              We sent a login link to <strong>{email}</strong>. Click it to sign
              in.
            </p>
            <button
              onClick={() => setStatus("idle")}
              className="mt-4 text-sm text-[#0D7377] hover:underline cursor-pointer"
            >
              Use a different email
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="text-left">
              <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
                Email address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
                placeholder="jane@example.com"
              />
            </div>

            {status === "error" && (
              <p className="text-sm text-red-600">{errorMsg}</p>
            )}

            <button
              type="submit"
              disabled={status === "sending"}
              className="w-full py-3 text-sm font-medium text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {status === "sending" ? "Sending..." : "Send Magic Link"}
            </button>

            <p className="text-xs text-gray-400">
              We'll send you a secure login link — no password needed.
            </p>
          </form>
        )}
      </div>

      <Footer />
    </div>
  );
}

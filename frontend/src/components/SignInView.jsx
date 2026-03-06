import { useState, useCallback } from "react";
import { supabase } from "../lib/supabase.js";
import EmailOtpInput from "./EmailOtpInput.jsx";
import { Footer } from "./UploadView.jsx";

export default function SignInView() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("idle"); // idle | sending | code | error
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      setStatus("sending");
      setErrorMsg("");

      const { error } = await supabase.auth.signInWithOtp({
        email,
      });

      if (error) {
        setStatus("error");
        setErrorMsg(error.message);
      } else {
        setStatus("code");
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

        {status === "code" ? (
          <div className="bg-[#0D7377]/5 border border-[#0D7377]/20 rounded-xl p-6">
            <EmailOtpInput
              email={email}
              onBack={() => { setStatus("idle"); setErrorMsg(""); }}
            />
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
              {status === "sending" ? "Sending..." : "Send Code"}
            </button>

            <p className="text-xs text-gray-400">
              We'll send you a secure code — no password needed.
            </p>
          </form>
        )}
      </div>

      <Footer />
    </div>
  );
}

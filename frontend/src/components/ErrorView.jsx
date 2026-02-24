import { Footer } from "./UploadView.jsx";

export default function ErrorView({ title, message, onReset }) {
  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-4 font-[Arial,sans-serif]">
      <div className="text-center max-w-md">
        <h1 className="text-4xl font-bold text-[#1B3A5C] mb-10 tracking-tight">
          Parity Health
        </h1>

        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-8">
          <svg
            className="w-10 h-10 text-amber-500 mx-auto mb-3"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
            />
          </svg>
          <h2 className="text-lg font-semibold text-[#1B3A5C] mb-2">
            {title}
          </h2>
          <p className="text-sm text-gray-600 leading-relaxed">{message}</p>
        </div>

        <button
          onClick={onReset}
          className="px-6 py-3 text-sm font-medium text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer"
        >
          Try Again
        </button>
      </div>

      <Footer />
    </div>
  );
}

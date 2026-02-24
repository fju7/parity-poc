import { Link } from "react-router-dom";

export default function LegalPage({ title, subtitle, effectiveDate, children }) {
  return (
    <div className="min-h-screen bg-white flex flex-col font-[Arial,sans-serif]">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white sticky top-0 z-50">
        <div className="max-w-3xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link
            to="/"
            className="text-sm text-[#0D7377] hover:text-[#0B6164] flex items-center gap-1.5 no-underline"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
            </svg>
            civicscale.ai
          </Link>
          <div className="text-right">
            <span className="text-sm font-semibold text-[#1B3A5C]">Parity Health</span>
            <span className="text-xs text-gray-400 ml-1.5">by CivicScale</span>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 max-w-3xl mx-auto px-6 py-12 w-full">
        <h1 className="text-3xl font-bold text-[#1B3A5C] mb-2">{title}</h1>
        {subtitle && <p className="text-gray-500 mb-4">{subtitle}</p>}
        {effectiveDate && (
          <p className="text-xs text-gray-400 mb-10">
            {effectiveDate}
          </p>
        )}
        <div className="legal-content text-gray-700 leading-relaxed text-[15px]">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-8 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <p className="text-xs text-gray-400">
            Parity Health is a product of CivicScale, operated by U.S. Photovoltaics, Inc., a Florida corporation.
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Questions: <a href="mailto:privacy@civicscale.ai" className="text-[#0D7377] hover:underline">privacy@civicscale.ai</a>
          </p>
        </div>
      </footer>
    </div>
  );
}

export function Section({ number, title, children }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold text-[#1B3A5C] mb-3">
        {number && <span className="text-[#0D7377] mr-1">{number}.</span>}
        {title}
      </h2>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

export function SubSection({ number, title, children }) {
  return (
    <div className="mb-4">
      <h3 className="text-[15px] font-semibold text-[#1B3A5C] mb-2">
        {number && <span className="text-gray-400 mr-1">{number}</span>}
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

export function BulletList({ items }) {
  return (
    <ul className="list-disc list-outside ml-5 space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="text-gray-700 text-[15px] leading-relaxed pl-1">{item}</li>
      ))}
    </ul>
  );
}

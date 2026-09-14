/**
 * What a reader sees at /:slug when the topic is not published.
 *
 * Since migration 078 the database admits a topic to the public reader only
 * when signal_issues.status = 'published'. A draft topic and a slug that was
 * never a topic look identical from here -- both return no row -- and that
 * is the honest thing to show: not an error, not an empty dashboard, and
 * not a hint at what is behind the gate. Employer, broker, provider and
 * health deep links (signal.civicscale.ai/<slug>) land here cleanly.
 */
export default function NotYetPublished({ slug }) {
  return (
    <div className="max-w-xl mx-auto px-4 py-16 font-[Arial,sans-serif]">
      <div className="text-xs font-semibold text-[#0D7377] bg-teal-50 px-2.5 py-0.5 rounded-full uppercase tracking-wide inline-block mb-4">
        Parity Signal
      </div>
      <h1 className="text-2xl font-bold text-[#1B3A5C] mb-3">Not yet published</h1>
      <p className="text-gray-600 text-sm leading-relaxed mb-3">
        Parity Signal topics are published one at a time, after every source behind a
        topic has been checked against the document it cites. This topic
        {slug ? <> (<span className="font-mono text-gray-500">{slug}</span>)</> : null} hasn&apos;t
        cleared that check — or doesn&apos;t exist.
      </p>
      <p className="text-gray-600 text-sm leading-relaxed mb-6">
        Nothing is being withheld that we&apos;d stand behind; there&apos;s simply nothing
        here we&apos;re willing to show yet.
      </p>
      <div className="flex gap-4 text-sm">
        <a href="/methodology" className="text-[#0D7377] font-medium hover:underline">
          How topics are checked →
        </a>
        <a href="/" className="text-[#0D7377] font-medium hover:underline">
          All topics →
        </a>
      </div>
    </div>
  );
}

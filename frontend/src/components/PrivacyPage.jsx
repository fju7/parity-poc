import LegalPage, { Section, SubSection, BulletList } from "./LegalPage.jsx";

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      subtitle="How CivicScale collects, uses, and protects your information across all products"
      effectiveDate="Effective Date: April 1, 2026 · Last Updated: April 1, 2026"
    >
      <Section number="1" title="Who We Are">
        <p>
          CivicScale is an institutional benchmark intelligence platform operated by U.S. Photovoltaics,
          Inc. (USPV, &ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;), a Florida corporation. CivicScale operates six products
          under the Parity brand, all powered by the Parity Engine:
        </p>
        <BulletList items={[
          "Parity Health (health.civicscale.ai) — consumer medical bill analysis",
          "Parity Employer (employer.civicscale.ai) — self-insured employer claims analytics",
          "Parity Broker (broker.civicscale.ai) — broker book-of-business management",
          "Parity Provider (provider.civicscale.ai) — provider contract integrity and denial intelligence",
          "Parity Billing (billing.civicscale.ai) — RCM platform for billing companies",
          "Parity Signal (signal.civicscale.ai) — AI-powered evidence scoring for complex topics",
        ]} />
        <p>
          This Privacy Policy applies to all six products and to civicscale.ai. It replaces all prior
          privacy policies. Questions or privacy
          requests: <a href="mailto:privacy@civicscale.ai" className="text-[#0D7377] hover:underline">privacy@civicscale.ai</a>.
        </p>
      </Section>

      <Section number="2" title="Our Core Privacy Commitments">
        <p className="font-medium text-[#1B3A5C]">
          These commitments apply across all CivicScale products:
        </p>
        <BulletList items={[
          "We never sell personal information or identifiable health data.",
          "We never use your data for advertising.",
          "We collect and store only what is necessary for each product to function.",
          "No patient names, member IDs, dates of birth, Social Security numbers, or diagnosis codes are extracted or stored from any file uploaded to any CivicScale product. This is an architectural constraint built into our parsers, not merely a policy promise.",
          "Raw uploaded files (835 EDI files, CSV files, Excel files, PDFs other than contracts) are processed in memory and discarded. They are never stored permanently.",
          "Row Level Security is enforced at the database level on all tables. Only your account can access your data.",
          "We do not store passwords. Authentication uses one-time passcode (OTP) codes sent via email.",
        ]} />
      </Section>

      <Section number="3" title="What Each Product Collects">
        <p>
          The data each product collects depends on its function. The table below summarizes the data
          profile for each product. Detailed descriptions follow.
        </p>
        <div className="overflow-x-auto mt-4 mb-4">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b-2 border-gray-200">
                <th className="text-left py-2 pr-3 font-semibold text-[#1B3A5C]">Product</th>
                <th className="text-left py-2 pr-3 font-semibold text-[#1B3A5C]">Risk Level</th>
                <th className="text-left py-2 pr-3 font-semibold text-[#1B3A5C]">Data Stored from Uploads</th>
                <th className="text-left py-2 pr-3 font-semibold text-[#1B3A5C]">Patient PII?</th>
                <th className="text-left py-2 font-semibold text-[#1B3A5C]">Raw Files Stored?</th>
              </tr>
            </thead>
            <tbody className="text-gray-600">
              <tr className="border-b border-gray-100">
                <td className="py-2 pr-3 font-medium text-gray-700">Parity Health</td>
                <td className="py-2 pr-3">None</td>
                <td className="py-2 pr-3">No uploads stored. Analysis runs in memory. Only procedure codes and zip code transmitted for benchmarks.</td>
                <td className="py-2 pr-3">None</td>
                <td className="py-2">None (by design)</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-2 pr-3 font-medium text-gray-700">Parity Employer</td>
                <td className="py-2 pr-3">Low</td>
                <td className="py-2 pr-3">Aggregate CPT codes, billed amounts, drug names, plan design data. No individual claim identifiers.</td>
                <td className="py-2 pr-3">None</td>
                <td className="py-2">None</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-2 pr-3 font-medium text-gray-700">Parity Broker</td>
                <td className="py-2 pr-3">Low</td>
                <td className="py-2 pr-3">Same as Employer — writes to employer tables. Plan-level benchmark data only.</td>
                <td className="py-2 pr-3">None</td>
                <td className="py-2">None</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-2 pr-3 font-medium text-gray-700">Parity Provider</td>
                <td className="py-2 pr-3">Moderate</td>
                <td className="py-2 pr-3">Claim-level records: claim_id, date of service, CPT codes, rendering provider NPI, denial codes, billed/paid amounts. No patient names or member IDs.</td>
                <td className="py-2 pr-3">None</td>
                <td className="py-2">None (contract PDFs in Supabase Storage)</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-2 pr-3 font-medium text-gray-700">Parity Billing</td>
                <td className="py-2 pr-3">Moderate</td>
                <td className="py-2 pr-3">Same as Provider plus denormalized billing_claim_lines table for recovery tracking. Contract PDFs stored in Supabase Storage.</td>
                <td className="py-2 pr-3">None</td>
                <td className="py-2">Contract PDFs only</td>
              </tr>
              <tr>
                <td className="py-2 pr-3 font-medium text-gray-700">Parity Signal</td>
                <td className="py-2 pr-3">None</td>
                <td className="py-2 pr-3">Email address, subscription tier, topic request history. No health data.</td>
                <td className="py-2 pr-3">None</td>
                <td className="py-2">None</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Section>

      <Section number="4" title="Product-by-Product Data Description">
        <SubSection number="4.1" title="Parity Health">
          <p className="italic text-gray-500">
            Privacy-by-architecture: your medical documents never leave your device.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">What we store in our cloud database:</p>
          <BulletList items={[
            "Your email address — used for authentication",
            "Your account profile (name, date of birth, mailing address, phone) — used solely to pre-fill bill request letters",
            "Your consent choices and dates",
            "Your subscription status",
          ]} />
          <p className="font-medium text-[#1B3A5C] mt-3">What stays on your device only:</p>
          <BulletList items={[
            "Your uploaded medical bill, EOB, or denial letter documents — processed entirely in your browser, never transmitted to our servers",
            "Your bill analysis results (CPT codes, billed amounts, benchmark comparisons, anomaly flags) — stored in your browser's local storage only",
          ]} />
          <p className="font-medium text-[#1B3A5C] mt-3">What is transmitted to our servers (no personal identifiers):</p>
          <BulletList items={[
            "Procedure codes (CPT codes), billed amounts, and your zip code — used for benchmark lookups only",
          ]} />
          <p>
            No patient PII, no diagnosis codes, no raw documents stored on our servers. This is an
            architectural guarantee that will not change.
          </p>
        </SubSection>

        <SubSection number="4.2" title="Parity Employer">
          <p className="font-medium text-[#1B3A5C]">What we store:</p>
          <BulletList items={[
            "Your account profile (email, company name, industry, state) — used to operate your account",
            "Aggregate analysis results from uploaded claims files — CPT code distributions, billed/paid amounts, anomaly flags, drug benchmarks. No individual claim identifiers are stored. No employee names or member IDs are extracted.",
            "Plan scorecard results from SBC uploads — plan design data (deductibles, copays, network type). No individual member data.",
            "Benchmark session results — percentile, dollar gap, AI narrative. No individual data.",
          ]} />
          <p className="font-medium text-[#1B3A5C] mt-3">What we do not store:</p>
          <BulletList items={[
            "Raw 835 EDI files, CSV files, or Excel files — processed in memory and discarded",
            "Employee names, member IDs, or any individual-level claim data",
            "Diagnosis codes",
          ]} />
        </SubSection>

        <SubSection number="4.3" title="Parity Broker">
          <p>
            Parity Broker&rsquo;s data profile is identical to Parity Employer. When brokers upload claims files
            on behalf of employer clients, those files are processed through the same employer claims pipeline
            with the same data minimization architecture. No individual claim data is stored. No patient PII
            is extracted.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">Broker-specific data stored:</p>
          <BulletList items={[
            "Your account profile (email, company name)",
            "Client benchmark results (company name, industry, state, benchmark percentile, dollar gap) — plan-level only, no individual data",
            "Prospect benchmark results — aggregate only",
            "Broker-employer connection records — company name, industry, carrier, contact email",
            "Referral history",
          ]} />
        </SubSection>

        <SubSection number="4.4" title="Parity Provider">
          <p className="font-medium text-[#1B3A5C]">What we store:</p>
          <BulletList items={[
            "Your account profile (email, practice name, specialty, NPI, zip code)",
            "Contract rate data you enter (CPT codes mapped to contracted rates by payer) — this is your own contract data",
            "Claim-level analysis records derived from your 835 remittance files: claim identifiers, dates of service, CPT codes, rendering provider NPI, denial codes, billed and paid amounts. These records are used to power contract integrity analysis, denial intelligence, and trend reporting.",
            "Aggregate benchmark observations — anonymized, de-identified, used to improve benchmarks across the platform",
          ]} />
          <p className="font-medium text-[#1B3A5C] mt-3">Important clarification on claim-level records:</p>
          <p>
            The claim-level records stored in Parity Provider contain no patient names, no patient member IDs,
            no dates of birth, no Social Security numbers, and no ICD-10 diagnosis codes. 835 remittance files
            contain CARC denial reason codes (e.g., CO-45, CO-16) but not diagnosis codes. The stored records
            identify individual claims and the rendering provider — they do not identify patients.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">What we do not store:</p>
          <BulletList items={[
            "Raw 835 EDI files — processed in memory and discarded after parsing",
            "Patient names, member IDs, dates of birth, SSNs, or diagnosis codes",
            "Contract PDF documents uploaded for rate extraction — stored in Supabase Storage under your account",
          ]} />
        </SubSection>

        <SubSection number="4.5" title="Parity Billing">
          <p>
            Parity Billing is designed for billing companies (RCM companies) that manage healthcare billing
            on behalf of multiple provider practices. Its data profile is similar to Parity Provider but
            operates at portfolio scale.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">What we store:</p>
          <BulletList items={[
            "Billing company profile (email, company name, subscription tier)",
            "Practice records — practice name, contact email, portal settings",
            "835 analysis results — same claim-level structure as Provider: claim identifiers, dates of service, CPT codes, provider names and NPIs, denial codes, billed and paid amounts. Stored in both result_json (per job) and billing_claim_lines (denormalized per line, used for cross-file recovery tracking).",
            "Contract PDFs uploaded for analysis — stored in Supabase Storage under your billing company account",
            "Escalation records — denial patterns, payer anomalies, status tracking",
            "Portal contact records — practice staff email addresses for portal access",
          ]} />
          <p className="font-medium text-[#1B3A5C] mt-3">What we do not store:</p>
          <BulletList items={[
            "Patient names, member IDs, dates of birth, SSNs, or diagnosis codes",
            "Raw 835 EDI files — temporarily held in the processing queue and cleared immediately after parsing",
          ]} />
          <p className="font-medium text-[#1B3A5C] mt-3">Note on the billing_claim_lines table:</p>
          <p>
            Parity Billing&rsquo;s recovery tracking feature requires a structured, queryable record of individual
            claim lines across multiple 835 files. This is why billing_claim_lines stores individual line-level
            records. These records contain claim numbers, CPT codes, dates of service, and adjudication data —
            but no patient identifiers.
          </p>
        </SubSection>

        <SubSection number="4.6" title="Parity Signal">
          <p>
            Parity Signal does not handle healthcare billing data. It is an evidence scoring platform for
            complex public topics.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">What we store:</p>
          <BulletList items={[
            "Your email address and authentication credentials",
            "Your subscription tier and payment status",
            "Topic request history (topics you have submitted for analysis)",
            "Usage data (questions asked per session, features accessed)",
          ]} />
          <p className="font-medium text-[#1B3A5C] mt-3">What we do not store:</p>
          <BulletList items={[
            "Any health, billing, or claims data",
            "Any personally identifiable health information of any kind",
          ]} />
        </SubSection>
      </Section>

      <Section number="5" title="Shared Infrastructure and Service Providers">
        <p>All CivicScale products are built on the following infrastructure:</p>
        <BulletList items={[
          "Supabase (PostgreSQL) — cloud database and file storage. Processes account and analysis data under data protection obligations. Does not use your data for its own purposes.",
          "Render — backend API hosting. Processes requests in memory. Does not retain data beyond request processing.",
          "Vercel — frontend hosting. Serves the application code only. Does not access user data.",
          "Anthropic Claude API — AI analysis provider. Uploaded documents and claims data are sent to the Claude API for analysis. Anthropic's data handling is governed by Anthropic's privacy policy and API terms. Claude API inputs are not used to train Anthropic's models under the standard API agreement.",
          "Resend — transactional email provider. Used for OTP authentication codes and system notifications.",
          "Stripe — payment processing. Handles subscription billing. CivicScale does not store payment card data.",
        ]} />
      </Section>

      <Section number="6" title="Authentication and Session Data">
        <p>
          All CivicScale products use one-time passcode (OTP) authentication. We do not store passwords.
          When you sign in, a time-limited code is sent to your email address. Verifying the code creates
          a session token stored in your browser&rsquo;s local storage.
        </p>
        <p>
          Session tokens expire after 30 days. Sessions are product-specific — your Parity Health session
          does not grant access to Parity Billing or any other product.
        </p>
      </Section>

      <Section number="7" title="Information Sharing">
        <p>
          We do not sell, rent, or trade personal information or identifiable health data. We share
          information only as follows:
        </p>
        <BulletList items={[
          "Service providers — Supabase, Render, Vercel, Anthropic, Resend, and Stripe process data on our behalf as described above. Each operates under data protection obligations.",
          "Anonymized aggregate data — with your permission, de-identified aggregate statistics derived from your analyses may be used to improve CivicScale products or shared with analytics partners and researchers. This data cannot identify you.",
          "Legal requirements — if required by law or valid court order. We will notify you if permitted to do so.",
          "Business transfer — if USPV is acquired or substantially all assets are transferred, your data may transfer as part of that transaction. We will notify you with the option to delete your account before transfer.",
        ]} />
      </Section>

      <Section number="8" title="A Note on HIPAA">
        <p>
          CivicScale is not a healthcare provider, health plan, or healthcare clearinghouse as defined by
          HIPAA. CivicScale products are analytics and benchmarking tools that process claims data on behalf
          of providers, employers, and billing companies.
        </p>
        <p>The following architectural facts are relevant to HIPAA classification:</p>
        <BulletList items={[
          "No patient names, member IDs, dates of birth, Social Security numbers, or ICD-10 diagnosis codes are extracted or stored by any CivicScale product. This is enforced at the parser level, not merely by policy.",
          "Parity Health processes medical documents entirely within the user's browser — no documents or analysis results are stored on our servers.",
          "Parity Employer and Parity Broker store only aggregate, de-identified statistical results from claims files.",
          "Parity Provider and Parity Billing store claim-level transaction records (claim identifiers, dates of service, CPT codes, provider NPIs) that are provider-identifiable but not patient-identifiable.",
        ]} />
        <p>
          CivicScale is committed to operating consistently with the spirit and intent of healthcare privacy
          law. If you have specific HIPAA compliance questions for your organization, please contact us
          at <a href="mailto:privacy@civicscale.ai" className="text-[#0D7377] hover:underline">privacy@civicscale.ai</a> to
          discuss your requirements.
        </p>
      </Section>

      <Section number="9" title="Data Security">
        <BulletList items={[
          "All data is encrypted in transit (TLS) and at rest",
          "Row Level Security (RLS) is enforced at the database level — only your authenticated account can access your data",
          "Session tokens are product-scoped and expire after 30 days",
          "No passwords are stored — OTP authentication only",
          "Supabase Storage is used for file storage with access-controlled, signed URLs",
          "We do not store payment card data — Stripe handles all payment processing",
        ]} />
      </Section>

      <Section number="10" title="Your Rights">
        <BulletList items={[
          "Access — view your account data at any time by signing in",
          "Correction — update your profile at any time from account settings",
          "Deletion — delete your account and all associated cloud-stored data at any time. Data is permanently deleted within 30 days.",
          "Data export — request your account data at privacy@civicscale.ai",
          "Consent withdrawal — withdraw analytics consent at any time from account settings with no effect on your service",
        ]} />
      </Section>

      <Section number="11" title="Data Retention">
        <p>
          We retain your account data for as long as your account is active. When you delete your account,
          all cloud-stored data associated with your account is permanently deleted within 30 days. We do
          not retain personal data after account deletion.
        </p>
        <p>
          For Parity Billing, claim line records associated with a practice are retained for the duration
          of the billing company&rsquo;s active subscription and deleted within 30 days of account termination.
        </p>
      </Section>

      <Section number="12" title="Children's Privacy">
        <p>
          CivicScale products are not directed to children under 13. We do not knowingly collect personal
          information from children under 13. If you believe a child under 13 has created an account,
          contact <a href="mailto:privacy@civicscale.ai" className="text-[#0D7377] hover:underline">privacy@civicscale.ai</a> and
          we will delete the account promptly.
        </p>
      </Section>

      <Section number="13" title="Changes to This Policy">
        <p>
          We will notify you by email and in-app notice at least 14 days before any material changes to
          this policy take effect. Continued use of CivicScale products after the effective date constitutes
          acceptance of the updated policy.
        </p>
      </Section>

      <Section number="14" title="Contact">
        <p>
          Privacy inquiries: <a href="mailto:privacy@civicscale.ai" className="text-[#0D7377] hover:underline">privacy@civicscale.ai</a>
          <br />
          General support: <a href="mailto:admin@civicscale.ai" className="text-[#0D7377] hover:underline">admin@civicscale.ai</a>
          <br />
          U.S. Photovoltaics, Inc. &middot; CivicScale &middot; Florida, United States
        </p>
        <p className="text-xs text-gray-400 italic mt-4">
          CivicScale Privacy Policy &middot; Effective April 1, 2026 &middot; U.S. Photovoltaics, Inc.
        </p>
      </Section>
    </LegalPage>
  );
}

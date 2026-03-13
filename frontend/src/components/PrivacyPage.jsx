import LegalPage, { Section, SubSection, BulletList } from "./LegalPage.jsx";

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      subtitle="How CivicScale and Parity Health collect, use, and protect your information"
      effectiveDate="Effective Date: March 1, 2026 · Last Updated: March 1, 2026"
    >
      <Section number="1" title="Who We Are">
        <p>
          CivicScale is an institutional benchmark infrastructure platform operated by U.S. Photovoltaics,
          Inc. (USPV, "we," "us," or "our"), a Florida corporation. Parity Health is CivicScale's healthcare
          product, which helps patients compare their medical bills against publicly available and licensed
          benchmark rates to identify potentially anomalous charges.
        </p>
        <p>
          This Privacy Policy applies to Parity Health and all CivicScale products.
          Questions: <a href="mailto:privacy@civicscale.ai" className="text-[#0D7377] hover:underline">privacy@civicscale.ai</a>
        </p>
      </Section>

      <Section number="2" title="Our Core Privacy Commitments">
        <p className="font-medium text-[#1B3A5C]">
          Your medical bill document never leaves your device. Your bill analysis results never leave your
          device. These are architectural guarantees built into how Parity Health works — not policy promises.
        </p>
        <p>
          Parity Health is built on a privacy-by-architecture principle that goes further than most health
          technology products:
        </p>
        <BulletList items={[
          "Your PDF medical bill is processed entirely within your browser. It is never uploaded, transmitted, or stored on any server.",
          "Your bill analysis results — including CPT codes, provider information, amounts, and anomaly flags — are stored only in your browser's local storage on your device. They never leave your device.",
          "Only the minimum information required for benchmark lookups is transmitted to our servers: procedure codes, billed amounts, and your zip code. This information contains no personal identifiers.",
          "Your account profile (name, date of birth, address, phone) is stored securely in our cloud database solely to pre-fill your request letters. It is never combined with your health data on our servers.",
        ]} />
        <p>
          This architecture was designed intentionally to eliminate the combination of personal identity and
          health information on our servers. We believe this is the right way to build health technology, and
          it is a structural commitment that will not change.
        </p>
      </Section>

      <Section number="3" title="Information We Collect and Where It Lives">
        <SubSection number="3.1" title="Account Profile — Stored in Our Cloud Database">
          <p>
            When you create a Parity Health account, we collect and store in our secure cloud database:
          </p>
          <BulletList items={[
            "Your email address — used for authentication",
            "Your first and last name",
            "Your date of birth",
            "Your mailing address (street, city, state, zip code)",
            "Your phone number",
            "Your consent choices and the date you made them",
          ]} />
          <p>
            This information is used exclusively to pre-fill your itemized bill request letters and to operate
            your account. It is never combined with your health data on our servers and is never sold.
          </p>
        </SubSection>

        <SubSection number="3.2" title="Bill Analysis Results — Stored on Your Device Only">
          <p>
            When you analyze a medical bill, the complete results are saved in your browser's local storage
            (IndexedDB) on your device. This includes:
          </p>
          <BulletList items={[
            "Provider name and date of service",
            "CPT codes and billed amounts",
            "Benchmark rates and sources",
            "Anomaly scores and flag reasons",
            "Summary totals and discrepancy calculations",
          ]} />
          <p>
            This data exists only on the device where you analyzed the bill. It is never transmitted to our
            servers. If you clear your browser data or use a different device, this history will not be
            available — which is why we provide an export feature so you can save your own copy.
          </p>
        </SubSection>

        <SubSection number="3.3" title="Anonymous Aggregate Analytics — Optional (Default: On)">
          <p>
            With your permission, which you can withdraw at any time, CivicScale may collect anonymized,
            aggregate statistical data derived from your bill analyses. This data is stripped of all personal
            identifiers before leaving your device and cannot be linked back to you.
          </p>
          <p>
            Examples: the percentage of bills in a given metro area with anomalous facility fees; the average
            ratio of billed-to-benchmark for a procedure category in a geographic region. No individual is
            identifiable in this data.
          </p>
          <p>
            This anonymized data helps us improve Parity Health, powers the employer aggregate dashboard, and
            may be used internally to improve CivicScale products and services. It is not PHI and does not
            identify you in any way. You can opt out at any time from My Account with no effect on your service.
          </p>
        </SubSection>

        <SubSection number="3.4" title="Employer Aggregate Dashboard — Optional (Default: Off)">
          <p>
            If your employer uses CivicScale's employer dashboard and you choose to opt in, your anonymized
            aggregate data will contribute to your employer's aggregate view of healthcare billing patterns.
            Your employer sees only aggregate statistics — never your individual bills, your identity, or any
            information that could identify you.
          </p>
          <p>
            This feature is off by default. You must actively opt in. You can opt out at any time. This has no
            effect on your employment or your access to Parity Health.
          </p>
        </SubSection>

        <SubSection number="3.5" title="Technical Information">
          <p>
            We may automatically collect basic technical information such as browser type, device type, and
            general usage patterns. This is used solely to maintain and improve the platform and is not linked
            to your health information.
          </p>
        </SubSection>
      </Section>

      <Section number="4" title="Your Three Data Choices">
        <p>
          During sign-up and at any time from My Account, you make three distinct choices:
        </p>
        <div className="space-y-4 mt-3">
          <div>
            <p className="font-medium text-[#1B3A5C]">Choice 1 — Core Service (Required)</p>
            <p>
              Your profile is stored in our cloud database to operate your account and pre-fill your request
              letters. Bill analysis results are stored on your device only. This is required to use Parity Health.
            </p>
          </div>
          <div>
            <p className="font-medium text-[#1B3A5C]">Choice 2 — Anonymous Analytics (Default: On, Can Opt Out)</p>
            <p>
              Anonymized, non-identifiable aggregate data derived from your bill analyses may be used to improve
              CivicScale products. You can turn this off at any time.
            </p>
          </div>
          <div>
            <p className="font-medium text-[#1B3A5C]">Choice 3 — Employer Aggregate Dashboard (Default: Off, Must Opt In)</p>
            <p>
              If your employer uses CivicScale, your anonymized aggregate data contributes to their workforce
              dashboard. Your identity is never revealed. You must actively turn this on.
            </p>
          </div>
        </div>
      </Section>

      <Section number="5" title="How We Use Your Information">
        <BulletList items={[
          "To provide the Parity Health bill analysis service",
          "To pre-fill your itemized bill request letters",
          "To send you magic link authentication emails",
          "To improve CivicScale products using anonymized aggregate data",
          "To power employer aggregate dashboards using anonymized aggregate data (with your opt-in)",
          "To respond to support requests",
        ]} />
        <p>
          We do not use your information for advertising. We do not sell personal information or identifiable
          health data.
        </p>
      </Section>

      <Section number="6" title="SMS and Phone Communications">
        <p>
          When you provide your phone number to receive a one-time passcode or other communications from
          CivicScale, your phone number and SMS opt-in consent will never be shared with, sold to, or
          transferred to any third party for any purpose whatsoever. Message and data rates may apply.
        </p>
      </Section>

      <Section number="7" title="Information Sharing">
        <p>We do not sell, rent, or trade your personal information or identifiable health data.</p>
        <p>We may share information only as follows:</p>
        <BulletList items={[
          "Anonymized aggregate data — with your consent, with analytics partners, researchers, and employer dashboard clients. This data cannot identify you.",
          "Service providers — Supabase processes account profile data on our behalf under data protection obligations. They do not use your data for their own purposes.",
          "Legal requirements — if required by law or court order. We will notify you if permitted to do so.",
          "Business transfer — if USPV is acquired, your data may transfer as part of that transaction. We will notify you with the option to delete your account before transfer.",
        ]} />
      </Section>

      <Section number="8" title="A Note on HIPAA">
        <p>
          Parity Health's privacy-by-architecture design means the combination of personal identity and health
          information never exists on our servers. Your health data (bill analysis results) stays on your
          device. Your identity data (profile) stays in our cloud database. We never join them in the cloud.
        </p>
        <p>
          This architecture is designed to eliminate the technical basis for HIPAA Business Associate
          classification in our consumer product. CivicScale is not a healthcare provider, health plan, or
          healthcare clearinghouse. We apply strong privacy and security practices consistent with the spirit
          of healthcare privacy law.
        </p>
      </Section>

      <Section number="9" title="Data Security">
        <p>
          Account profile data is stored using industry-standard encryption at rest and in transit. Row Level
          Security ensures only you can access your own data at the database level. Authentication uses magic
          link email — we never store passwords.
        </p>
        <p>
          Bill analysis data is stored in your browser's local storage (IndexedDB), protected by your
          device's own security.
        </p>
      </Section>

      <Section number="10" title="Your Rights">
        <BulletList items={[
          "Access — view all account information at any time by signing in",
          "Correction — update your profile at any time from My Account",
          "Deletion — delete your account and all cloud-stored data at any time. Data is permanently deleted within 30 days.",
          "Data export — download your bill history from the app, or request your account data at privacy@civicscale.ai",
          "Consent withdrawal — change analytics or employer preferences at any time from My Account",
        ]} />
      </Section>

      <Section number="11" title="Data Retention">
        <p>
          We retain your account profile for as long as your account is active. When you delete your account,
          all cloud-stored data is permanently deleted within 30 days. We do not retain data after deletion.
        </p>
      </Section>

      <Section number="12" title="Children's Privacy">
        <p>
          Parity Health is not directed to children under 13. We do not knowingly collect personal information
          from children under 13.
          Contact <a href="mailto:privacy@civicscale.ai" className="text-[#0D7377] hover:underline">privacy@civicscale.ai</a> if
          you believe a child under 13 has created an account.
        </p>
      </Section>

      <Section number="13" title="Changes to This Policy">
        <p>
          We will notify you by email and in-app notice before any material changes take effect. Continued use
          after the effective date constitutes acceptance.
        </p>
      </Section>

      <Section number="14" title="Contact">
        <p>
          Email: <a href="mailto:privacy@civicscale.ai" className="text-[#0D7377] hover:underline">privacy@civicscale.ai</a>
          <br />
          U.S. Photovoltaics, Inc. &middot; CivicScale &middot; Florida, United States
        </p>
      </Section>
    </LegalPage>
  );
}

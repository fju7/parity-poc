import LegalPage, { Section, SubSection, BulletList } from "./LegalPage.jsx";

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of Service"
      subtitle="Please read these terms carefully before using Parity Health"
      effectiveDate="Effective Date: March 1, 2026 · Last Updated: March 1, 2026"
    >
      <Section number="1" title="Agreement to Terms">
        <p>
          These Terms of Service govern your use of Parity Health, a product of CivicScale operated by
          U.S. Photovoltaics, Inc. (USPV, "we," "us," or "our"), a Florida corporation. By creating an
          account or using Parity Health, you agree to these Terms and our Privacy Policy. If you do not
          agree, do not use Parity Health.
        </p>
      </Section>

      <Section number="2" title="About CivicScale and Parity Health">
        <p>
          CivicScale is an institutional benchmark infrastructure platform. Parity Health is CivicScale's
          healthcare product — the first implementation of the Parity benchmark intelligence engine applied
          to medical billing. CivicScale operates additional verticals under the Parity name (Parity Property,
          Parity Insurance, Parity Finance) using the same underlying infrastructure.
        </p>
      </Section>

      <Section number="3" title="What Parity Health Is — and Is Not">
        <SubSection number="3.1" title="What Parity Health Does">
          <p>
            Parity Health helps you compare charges on your medical bills against publicly available and
            licensed benchmark rates, including Medicare rates published by CMS and negotiated rates from
            third-party data providers. Parity Health identifies charges that appear statistically anomalous
            and helps you request itemized bills from providers.
          </p>
        </SubSection>
        <SubSection number="3.2" title="What Parity Health Is Not">
          <BulletList items={[
            "Legal advice — Parity Health is not a substitute for a qualified attorney",
            "Medical advice — Parity Health does not provide clinical guidance",
            "Financial advice — Parity Health does not provide financial recommendations",
            "A guarantee of savings — outcomes depend on many factors outside our control",
            "A determination of fraud — an anomalous charge is not a finding of fraud; billing errors have many causes",
          ]} />
          <p className="mt-3">
            Always consult qualified professionals before taking action on medical billing matters.
          </p>
        </SubSection>
      </Section>

      <Section number="4" title="Privacy Architecture — Your Core Guarantee">
        <p>
          Your medical bill document and your bill analysis results never leave your device. This is an
          architectural guarantee built into how Parity Health works, not merely a policy promise.
        </p>
        <p>By using Parity Health you acknowledge and agree that:</p>
        <BulletList items={[
          "Bill analysis is performed entirely within your browser",
          "Bill analysis results are stored only in your browser's local storage on your device",
          "Only procedure codes, amounts, and zip code are transmitted to our servers for benchmark lookups — no personal identifiers",
          "Your account profile is stored in our cloud database but never combined with your health data on our servers",
        ]} />
      </Section>

      <Section number="5" title="Your Data Choices">
        <p>
          During account creation you will be presented with three clearly labeled choices regarding your
          data, described in detail in our Privacy Policy. In summary:
        </p>
        <BulletList items={[
          "Core Service (required) — profile stored in cloud, health data stored on your device only",
          "Anonymous Analytics (default on, can opt out) — anonymized aggregate data may be used to improve CivicScale products",
          "Employer Dashboard (default off, must opt in) — anonymized aggregate data contributes to your employer's workforce dashboard if your employer uses CivicScale",
        ]} />
      </Section>

      <Section number="6" title="Eligibility">
        <p>
          You must be at least 18 years of age to use Parity Health. By using Parity Health, you represent
          that you are at least 18 and have the legal capacity to enter into these Terms.
        </p>
      </Section>

      <Section number="7" title="Your Account">
        <p>
          You are responsible for providing accurate profile information, keeping your email account secure,
          and all activity under your account. You may delete your account at any time from My Account. Upon
          deletion, all cloud-stored data is permanently removed within 30 days.
        </p>
      </Section>

      <Section number="8" title="SMS and Phone Communications">
        <p>
          When you provide your phone number to receive a one-time passcode or other communications from
          CivicScale, your phone number and SMS opt-in consent will never be shared with, sold to, or
          transferred to any third party for any purpose whatsoever. Message and data rates may apply.
        </p>
      </Section>

      <Section number="9" title="Acceptable Use">
        <p>You agree not to:</p>
        <BulletList items={[
          "Use Parity Health to analyze bills for which you do not have authorization",
          "Attempt to reverse engineer, decompile, or extract source code from Parity Health or CivicScale",
          "Use automated tools to scrape data from CivicScale products",
          "Attempt to gain unauthorized access to CivicScale infrastructure",
          "Upload malicious files or attempt to exploit security vulnerabilities",
          "Attempt to re-identify anonymized aggregate data",
        ]} />
      </Section>

      <Section number="10" title="Benchmark Data and Accuracy">
        <p>
          Parity Health uses CMS Medicare rate data and, where available, third-party negotiated rate data
          licensed by CivicScale. We make reasonable efforts to keep this data current but do not guarantee
          accuracy or completeness at any given time.
        </p>
        <p>
          Medicare rates are not the same as the rates your insurer has negotiated with your provider. A
          charge that exceeds a benchmark rate is not necessarily incorrect. Use Parity Health output as a
          starting point for inquiry, not a definitive determination.
        </p>
      </Section>

      <Section number="11" title="Local Storage and Data Responsibility">
        <p>
          Because your bill analysis results are stored in your browser's local storage on your device, you
          are responsible for:
        </p>
        <BulletList items={[
          "Maintaining access to the device where you analyzed your bills",
          "Exporting your bill history if you wish to preserve it across devices or browser resets",
          "Understanding that clearing your browser data will delete your local bill history",
        ]} />
        <p>
          We provide an export feature for this purpose. CivicScale is not liable for loss of locally stored
          data resulting from device loss, browser clearing, or other actions taken on your device.
        </p>
      </Section>

      <Section number="12" title="Intellectual Property">
        <p>
          CivicScale, Parity Health, and the Parity benchmark intelligence engine are owned by U.S.
          Photovoltaics, Inc. and protected by applicable intellectual property laws. CMS Medicare rate data
          is publicly available and published by the U.S. Department of Health and Human Services.
        </p>
      </Section>

      <Section number="13" title="Disclaimer of Warranties">
        <p className="uppercase text-sm font-medium text-gray-600">
          Parity Health is provided "as is" and "as available" without warranties of any kind, either express
          or implied. We do not warrant that Parity Health will be uninterrupted, error-free, or completely
          secure.
        </p>
      </Section>

      <Section number="14" title="Limitation of Liability">
        <p className="uppercase text-sm font-medium text-gray-600">
          To the maximum extent permitted by applicable law, U.S. Photovoltaics, Inc. shall not be liable
          for any indirect, incidental, special, consequential, or punitive damages arising from your use of
          Parity Health, including loss of locally stored bill history data. Our total liability shall not
          exceed the amount you paid us in the twelve months preceding the claim (or $100 if you have not
          paid us anything).
        </p>
      </Section>

      <Section number="15" title="Indemnification">
        <p>
          You agree to indemnify and hold harmless U.S. Photovoltaics, Inc. and its officers, directors,
          employees, and agents from any claims, damages, or expenses arising from your use of Parity Health
          or your violation of these Terms.
        </p>
      </Section>

      <Section number="16" title="Governing Law">
        <p>
          These Terms are governed by the laws of the State of Florida. Any disputes shall be resolved in the
          courts of Florida.
        </p>
      </Section>

      <Section number="17" title="Changes to These Terms">
        <p>
          We will notify you by email and in-app notice at least 14 days before material changes take effect.
          Continued use after the effective date constitutes acceptance.
        </p>
      </Section>

      <Section number="18" title="Termination">
        <p>
          We reserve the right to suspend or terminate your account for violations of these Terms. You may
          terminate at any time from My Account. Data deletion follows our Privacy Policy upon termination.
        </p>
      </Section>

      <Section number="19" title="Contact">
        <p>
          Email: <a href="mailto:privacy@civicscale.ai" className="text-[#0D7377] hover:underline">privacy@civicscale.ai</a>
          <br />
          U.S. Photovoltaics, Inc. &middot; CivicScale &middot; Florida, United States
        </p>
      </Section>
    </LegalPage>
  );
}

import LegalPage, { Section, SubSection, BulletList } from "./LegalPage.jsx";

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of Service"
      subtitle="Please read these terms carefully before using any CivicScale product"
      effectiveDate="Effective Date: April 1, 2026 · Last Updated: April 1, 2026"
    >
      <Section number="1" title="Agreement to Terms">
        <p>
          These Terms of Service (&ldquo;Terms&rdquo;) govern your use of all CivicScale products operated by U.S.
          Photovoltaics, Inc. (USPV, &ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;), a Florida corporation. By creating an
          account or using any CivicScale product, you agree to these Terms and our Privacy Policy. If you
          do not agree, do not use CivicScale products.
        </p>
      </Section>

      <Section number="2" title="About CivicScale">
        <p>
          CivicScale is an institutional benchmark intelligence platform. All six products share the Parity
          Engine — a common AI-powered analytical infrastructure for benchmark analysis, evidence scoring,
          and information transparency:
        </p>
        <BulletList items={[
          "Parity Health — consumer medical bill analysis",
          "Parity Employer — self-insured employer claims analytics",
          "Parity Broker — broker book-of-business management",
          "Parity Provider — provider contract integrity and denial intelligence",
          "Parity Billing — RCM platform for billing companies managing provider practices",
          "Parity Signal — AI-powered evidence scoring for complex public topics",
        ]} />
      </Section>

      <Section number="3" title="What CivicScale Products Are — and Are Not">
        <SubSection number="3.1" title="What CivicScale Does">
          <p>
            CivicScale products apply publicly available benchmark data, contractually established rates,
            and AI analysis to help users identify information asymmetries in healthcare billing, insurance,
            and public information. Products compare charges, claims, and contracts against benchmark
            standards and generate analysis to support informed decision-making.
          </p>
        </SubSection>
        <SubSection number="3.2" title="What CivicScale Is Not">
          <BulletList items={[
            "Legal advice — CivicScale products are not a substitute for a qualified attorney",
            "Medical advice — CivicScale products do not provide clinical guidance",
            "Financial advice — CivicScale products do not provide financial recommendations",
            "A guarantee of outcomes — results depend on many factors outside our control",
            "A determination of fraud — an anomalous charge or underpayment flag is not a finding of fraud; billing errors and system errors have many causes",
            "A substitute for professional billing or coding expertise",
          ]} />
          <p className="mt-3">
            Always consult qualified professionals before taking action on billing, legal, or financial matters.
          </p>
        </SubSection>
      </Section>

      <Section number="4" title="Eligibility">
        <p>
          You must be at least 18 years of age to use any CivicScale product. By using CivicScale products,
          you represent that you are at least 18 and have the legal capacity to enter into these Terms.
        </p>
        <p>
          For Parity Billing and Parity Employer, by using the product you also represent that you are
          authorized to upload and analyze the claims files and documents you submit. You must have
          appropriate authorization from the relevant employer, practice, or billing company.
        </p>
      </Section>

      <Section number="5" title="Pricing and Subscriptions">
        <p>
          Current pricing for all CivicScale products is published at civicscale.ai and on each product&rsquo;s
          pricing page. Prices may change at any time with 30 days&rsquo; notice to active subscribers. Early
          subscribers who accept introductory pricing are locked at that rate for 24 months from their
          subscription start date.
        </p>
        <p>
          All subscriptions are billed through Stripe. CivicScale does not store payment card data. You may
          cancel your subscription at any time from your account settings; access continues through the end
          of the paid period. Refunds are not provided for partial billing periods.
        </p>
      </Section>

      <Section number="6" title="Product-Specific Terms">
        <SubSection number="6.1" title="Parity Health">
          <p className="font-medium text-[#1B3A5C]">Privacy architecture guarantee:</p>
          <p>
            Your uploaded medical bill documents and bill analysis results never leave your device. This is an
            architectural guarantee built into how Parity Health works — not merely a policy promise. Bill
            analysis is performed entirely within your browser. Only procedure codes, amounts, and your zip
            code are transmitted to our servers for benchmark lookups. No personal identifiers are transmitted.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">Local storage responsibility:</p>
          <p>
            Because bill analysis results are stored in your browser&rsquo;s local storage, you are responsible for
            exporting your history if you wish to preserve it across devices or browser resets. CivicScale is
            not liable for loss of locally stored data resulting from device loss, browser clearing, or other
            actions taken on your device. We provide an export feature for this purpose.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">Data choices:</p>
          <p>
            During sign-up and at any time from account settings, you control three data choices: (1) core
            service — required; (2) anonymous analytics — default on, can opt out; (3) employer aggregate
            dashboard — default off, must opt in. Details in our Privacy Policy.
          </p>
        </SubSection>

        <SubSection number="6.2" title="Parity Employer">
          <p className="font-medium text-[#1B3A5C]">Authorized uploads:</p>
          <p>
            By uploading claims files to Parity Employer, you represent that you are authorized to share those
            files for analysis purposes on behalf of the employer. You agree not to upload claims files
            containing data for individuals who have not authorized such use under your organization&rsquo;s
            applicable policies.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">Data minimization:</p>
          <p>
            Parity Employer stores only aggregate, de-identified statistical results from claims files. Raw 835
            EDI files, CSV files, and Excel files are processed in memory and discarded. No individual employee
            or member data is extracted or stored. See our Privacy Policy for details.
          </p>
        </SubSection>

        <SubSection number="6.3" title="Parity Broker">
          <p className="font-medium text-[#1B3A5C]">Client authorization:</p>
          <p>
            By uploading claims files or plan documents on behalf of employer clients, you represent that you
            have appropriate authorization from each client to analyze their data using CivicScale. You are
            responsible for maintaining appropriate client engagement agreements that authorize this use.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">Shared benchmark reports:</p>
          <p>
            Benchmark reports shared with employer clients via Parity Broker&rsquo;s share link feature are
            accessible to anyone with the link. You are responsible for sharing links only with intended
            recipients.
          </p>
        </SubSection>

        <SubSection number="6.4" title="Parity Provider">
          <p className="font-medium text-[#1B3A5C]">835 file authorization:</p>
          <p>
            By uploading 835 remittance files to Parity Provider, you represent that you are the billing
            provider, practice administrator, or an authorized representative with the right to analyze those
            remittance files.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">Claim-level data:</p>
          <p>
            Parity Provider stores claim-level transaction records derived from your 835 files (claim
            identifiers, dates of service, CPT codes, provider NPIs, denial codes, amounts) to power contract
            integrity analysis and trend reporting. These records contain no patient PII. See our Privacy Policy
            for details. You may request deletion of your analysis history at any time by deleting your account
            or contacting <a href="mailto:privacy@civicscale.ai" className="text-[#0D7377] hover:underline">privacy@civicscale.ai</a>.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">Contract rates:</p>
          <p>
            Contract rate data you enter (CPT codes mapped to contracted rates by payer) is stored under your
            account and used solely to power your contract integrity analysis. This data is not shared with
            other users.
          </p>
        </SubSection>

        <SubSection number="6.5" title="Parity Billing">
          <p className="font-medium text-[#1B3A5C]">Billing company / practice relationship:</p>
          <p>
            Parity Billing is designed for billing companies (RCM companies) that manage healthcare billing on
            behalf of multiple provider practices. The billing company account is the primary account. Practices
            are sub-accounts linked to the billing company. Analysts assigned to specific practices can access
            only those practices.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">Practice client portal:</p>
          <p>
            The practice client portal allows billing companies to share analysis data with their practice
            clients through a separate, gated login. Portal access is controlled entirely by the billing company
            administrator. Portal contacts (practice staff email addresses) are stored under the billing company
            account. CivicScale is not responsible for the accuracy of portal contact lists maintained by billing
            companies.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">835 file authorization:</p>
          <p>
            By uploading 835 remittance files on behalf of provider practices, billing companies represent that
            they have appropriate authorization from each practice to analyze those files using CivicScale.
            Billing companies are responsible for maintaining appropriate client engagement agreements.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">Claim-level data and retention:</p>
          <p>
            Parity Billing stores claim-level transaction records and denormalized claim line data
            (billing_claim_lines) to power cross-file recovery tracking and portfolio analytics. These records
            contain no patient PII. Claim line records are retained for the duration of the active subscription
            and deleted within 30 days of account termination. See our Privacy Policy for details.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">Subscription tiers and practice limits:</p>
          <p>
            Parity Billing subscription tiers are based on the number of practices managed. Current tier limits
            and pricing are published at billing.civicscale.ai. Adding practices beyond your tier limit requires
            upgrading your subscription.
          </p>
        </SubSection>

        <SubSection number="6.6" title="Parity Signal">
          <p className="font-medium text-[#1B3A5C]">Evidence scoring methodology:</p>
          <p>
            Parity Signal scores claims about complex public topics against available evidence using a
            transparent, documented methodology. Signal scores represent the current state of available evidence,
            not editorial positions. Evidence assessments are updated as new research becomes available.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">Topic requests:</p>
          <p>
            Paid subscribers may submit topic requests. CivicScale reviews all requests and determines which
            topics to analyze based on editorial judgment, feasibility, and platform guidelines. Submission of a
            topic request does not guarantee analysis or publication. Topic request fees, if any, are
            non-refundable.
          </p>
          <p className="font-medium text-[#1B3A5C] mt-3">Subscription tiers:</p>
          <p>
            Parity Signal offers a permanent free tier with limited access and paid subscription tiers with
            expanded access. Current tier limits and pricing are published at signal.civicscale.ai/pricing.
          </p>
        </SubSection>
      </Section>

      <Section number="7" title="Acceptable Use">
        <p>You agree not to:</p>
        <BulletList items={[
          "Upload claims files, documents, or data for which you do not have authorization",
          "Attempt to reverse engineer, decompile, or extract source code from any CivicScale product",
          "Use automated tools to scrape, bulk-download, or systematically extract data from any CivicScale product",
          "Attempt to gain unauthorized access to CivicScale infrastructure, databases, or other users' accounts",
          "Upload malicious files or attempt to exploit security vulnerabilities",
          "Attempt to re-identify anonymized aggregate data",
          "Use CivicScale products to facilitate fraud, misrepresentation, or any unlawful purpose",
          "Resell or sublicense access to CivicScale products without written authorization from USPV",
        ]} />
      </Section>

      <Section number="8" title="Benchmark Data and Accuracy">
        <p>
          CivicScale products use CMS Medicare rate data published by the Centers for Medicare and Medicaid
          Services, third-party rate data licensed by CivicScale where applicable, and publicly available
          research and regulatory data. We make reasonable efforts to keep this data current but do not
          guarantee accuracy or completeness at any given time.
        </p>
        <p>
          Medicare rates and published benchmarks are not the same as the rates any specific insurer has
          negotiated with any specific provider. A charge that exceeds a benchmark is not necessarily incorrect.
          A claim identified as potentially underpaid may have a legitimate explanation. Use CivicScale output
          as a starting point for inquiry and analysis, not a definitive determination.
        </p>
      </Section>

      <Section number="9" title="AI-Generated Analysis">
        <p>
          CivicScale products use the Anthropic Claude API to generate analysis, narratives, appeal letters,
          and other AI-generated content. AI-generated content is provided for informational purposes only.
          It may contain errors, omissions, or outdated information.
        </p>
        <p>
          Appeal letters, denial analyses, contractor scorecards, and other AI-generated documents produced
          by CivicScale products are starting points for your review and action — not final determinations
          or legal documents. Always review AI-generated content before submitting it to any payer, employer,
          or third party.
        </p>
      </Section>

      <Section number="10" title="Intellectual Property">
        <p>
          CivicScale, Parity Health, Parity Employer, Parity Broker, Parity Provider, Parity Billing, Parity
          Signal, and the Parity Engine are owned by U.S. Photovoltaics, Inc. and protected by applicable
          intellectual property laws. CMS Medicare rate data is publicly available and published by the U.S.
          Department of Health and Human Services.
        </p>
        <p>
          You retain ownership of any data you upload to CivicScale products. By uploading data, you grant
          CivicScale a limited license to process that data for the purpose of providing the service you
          requested.
        </p>
      </Section>

      <Section number="11" title="Disclaimer of Warranties">
        <p className="uppercase text-sm font-medium text-gray-600">
          CivicScale products are provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo; without warranties of any kind,
          either express or implied, including without limitation warranties of merchantability, fitness for
          a particular purpose, or non-infringement. We do not warrant that CivicScale products will be
          uninterrupted, error-free, or completely secure. Benchmark data and AI-generated analysis are
          provided for informational purposes and are not guaranteed to be accurate, complete, or current.
        </p>
      </Section>

      <Section number="12" title="Limitation of Liability">
        <p className="uppercase text-sm font-medium text-gray-600">
          To the maximum extent permitted by applicable law, U.S. Photovoltaics, Inc. shall not be liable
          for any indirect, incidental, special, consequential, or punitive damages arising from your use of
          CivicScale products, including but not limited to loss of locally stored data, incorrect benchmark
          analysis, AI-generated content errors, or actions taken in reliance on CivicScale output. Our total
          liability shall not exceed the amount you paid us in the twelve months preceding the claim (or $100
          if you have not paid us anything).
        </p>
      </Section>

      <Section number="13" title="Indemnification">
        <p>
          You agree to indemnify and hold harmless U.S. Photovoltaics, Inc. and its officers, directors,
          employees, and agents from any claims, damages, or expenses (including reasonable attorneys&rsquo; fees)
          arising from: (a) your use of CivicScale products; (b) your violation of these Terms; (c) your
          upload of data you were not authorized to share; or (d) any action you take in reliance on CivicScale
          output.
        </p>
      </Section>

      <Section number="14" title="Governing Law">
        <p>
          These Terms are governed by the laws of the State of Florida without regard to conflict of law
          principles. Any disputes arising from these Terms or your use of CivicScale products shall be
          resolved in the state or federal courts located in Florida, and you consent to personal jurisdiction
          in those courts.
        </p>
      </Section>

      <Section number="15" title="Changes to These Terms">
        <p>
          We will notify you by email and in-app notice at least 14 days before any material changes to these
          Terms take effect. Continued use of CivicScale products after the effective date constitutes
          acceptance of the updated Terms.
        </p>
      </Section>

      <Section number="16" title="Termination">
        <p>
          We reserve the right to suspend or terminate your account for violations of these Terms, at our
          discretion and with reasonable notice where practicable. You may terminate your account at any time
          from account settings. Data deletion upon termination follows our Privacy Policy.
        </p>
      </Section>

      <Section number="17" title="Contact">
        <p>
          Privacy inquiries: <a href="mailto:privacy@civicscale.ai" className="text-[#0D7377] hover:underline">privacy@civicscale.ai</a>
          <br />
          General support: <a href="mailto:admin@civicscale.ai" className="text-[#0D7377] hover:underline">admin@civicscale.ai</a>
          <br />
          U.S. Photovoltaics, Inc. &middot; CivicScale &middot; Florida, United States
        </p>
        <p className="text-xs text-gray-400 italic mt-4">
          CivicScale Terms of Service &middot; Effective April 1, 2026 &middot; U.S. Photovoltaics, Inc.
        </p>
      </Section>
    </LegalPage>
  );
}

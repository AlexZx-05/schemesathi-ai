import { ExternalLink, ShieldCheck } from "lucide-react";

import { Card } from "../components/ui/Card";

export function AboutPage() {
  return (
    <section aria-labelledby="about-title" className="page page--narrow">
      <p className="eyebrow">About SchemeSathi AI</p>
      <h1 className="page-title" id="about-title">
        Your Guide to Government Opportunities
      </h1>
      <p className="page-intro">
        SchemeSathi AI is an independent project designed to make information
        about public-benefit schemes easier to navigate.
      </p>
      <Card className="about-card">
        <span className="capability-icon capability-icon--3">
          <ShieldCheck aria-hidden="true" size={21} />
        </span>
        <h2>Independent, not official</h2>
        <p>
          SchemeSathi AI is not a government website, does not represent a
          government department, and does not determine eligibility or approve
          applications. Any future eligibility information will be preliminary
          and should be checked against current official guidelines.
        </p>
      </Card>
      <a
        className="official-source-link"
        href="https://www.india.gov.in/"
        rel="noreferrer"
        target="_blank"
      >
        National Portal of India
        <ExternalLink aria-hidden="true" size={15} />
      </a>
    </section>
  );
}

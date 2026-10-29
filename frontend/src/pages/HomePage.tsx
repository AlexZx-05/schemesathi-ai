import {
  ArrowRight,
  Bot,
  CheckSquare2,
  ExternalLink,
  FileText,
  Search,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { Card } from "../components/ui/Card";

const capabilities = [
  {
    icon: UserRound,
    title: "Personalized",
    detail: "recommendations",
  },
  {
    icon: CheckSquare2,
    title: "Eligibility",
    detail: "guidance",
  },
  {
    icon: FileText,
    title: "Document",
    detail: "checklists",
  },
  {
    icon: ExternalLink,
    title: "Official",
    detail: "source links",
  },
];

export function HomePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = searchQuery.trim();
    navigate(query ? `/schemes?q=${encodeURIComponent(query)}` : "/schemes");
  }

  return (
    <div className="page page--home">
      <section aria-labelledby="hero-title" className="hero">
        <div className="hero-content">
          <p className="hero-badge">
            <Bot aria-hidden="true" size={19} />
            Scheme information, made easier to navigate
          </p>
          <h1 id="hero-title">
            Discover
            <br />
            <span className="hero-highlight">Government Benefits</span>
            <br />
            That Are Right for You
          </h1>
          <p className="hero-description">
            Find clearer information about public-benefit schemes, understand
            preliminary requirements, and know where to verify official
            application details.
          </p>
          <form
            aria-label="Search schemes"
            className="search-callout"
            onSubmit={handleSearch}
            role="search"
          >
            <Search
              aria-hidden="true"
              className="search-callout-icon"
              size={21}
            />
            <input
              aria-label="Search scheme records"
              className="search-callout-input"
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search by scheme, category, or beneficiary..."
              type="search"
              value={searchQuery}
            />
            <button
              aria-label="Search schemes"
              className="search-callout-button"
              type="submit"
            >
              <ArrowRight aria-hidden="true" size={21} />
            </button>
          </form>
          <p className="source-note">
            Published scheme records are reviewed against official sources.
            Confirm the latest details with the issuing authority.
          </p>
          <p className="hero-note">
            <ShieldCheck aria-hidden="true" size={15} />
            Independent civic-tech project · Not an official government service
          </p>
          <div aria-label="Available guidance areas" className="capability-strip">
            {capabilities.map(({ detail, icon: Icon, title }, index) => (
              <div className="capability-item" key={title}>
                <span
                  className={`capability-icon capability-icon--${index + 1}`}
                >
                  <Icon aria-hidden="true" size={21} />
                </span>
                <span>
                  {title}
                  <br />
                  {detail}
                </span>
              </div>
            ))}
          </div>
          <p className="capability-note">
            Guidance is informational and does not guarantee eligibility or
            approval.
          </p>
        </div>

        <div className="hero-art">
          <img
            alt="Students and a farmer in front of an illustration of India’s Parliament and landscape"
            className="hero-image"
            height="768"
            src="/images/scheme-opportunities-hero.png"
            width="1024"
          />
        </div>
      </section>

      <section aria-labelledby="approach-title" className="approach-section">
        <div className="section-heading">
          <p className="eyebrow">A more helpful starting point</p>
          <h2 id="approach-title">
            Understand your next steps with confidence.
          </h2>
          <p>
            SchemeSathi AI organizes public-benefit information and points
            people back to the official sources that publish it.
          </p>
        </div>
        <div className="capability-grid">
          <Card className="capability-card">
            <span className="capability-icon capability-icon--1">
              <Bot aria-hidden="true" size={21} />
            </span>
            <h3>Plain-language information</h3>
            <p>
              A clearer starting point for learning what a scheme is intended to
              provide.
            </p>
          </Card>
          <Card className="capability-card">
            <span className="capability-icon capability-icon--2">
              <CheckSquare2 aria-hidden="true" size={21} />
            </span>
            <h3>Preliminary requirements</h3>
            <p>
              Guidance designed to help you prepare questions and details to
              verify.
            </p>
          </Card>
          <Card className="capability-card">
            <span className="capability-icon capability-icon--3">
              <ExternalLink aria-hidden="true" size={21} />
            </span>
            <h3>Official sources first</h3>
            <p>
              Current eligibility rules and applications should always be
              confirmed with the relevant authority.
            </p>
          </Card>
        </div>
      </section>

      <section aria-labelledby="faq-title" className="faq-section" id="faq">
        <div className="section-heading">
          <p className="eyebrow">A few important things to know</p>
          <h2 id="faq-title">Frequently asked questions</h2>
        </div>
        <div className="faq-list">
          <details>
            <summary>Is SchemeSathi AI an official government website?</summary>
            <p>
              No. SchemeSathi AI is an independent civic-tech project and is not
              affiliated with or endorsed by a government department.
            </p>
          </details>
          <details>
            <summary>
              Can I search schemes or check my eligibility?
            </summary>
            <p>
              You can browse scheme records that have completed source review.
              If no records are listed, there are currently no reviewed
              records available in the catalogue. Eligibility guidance is
              preliminary; always confirm current requirements with the
              responsible government authority.
            </p>
          </details>
        </div>
      </section>

      <aside aria-label="Important information" className="disclaimer">
        <ShieldCheck aria-hidden="true" size={21} />
        <p>
          <strong>Always verify before you apply.</strong> Scheme rules and
          deadlines can change. Confirm current requirements with the relevant
          government department or official portal.
        </p>
      </aside>
    </div>
  );
}

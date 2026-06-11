import Link from "next/link";

import ContactForm from "./ContactForm";

const workflowSteps = [
  {
    title: "Analyze your skin",
    text: "Skin photos and intake answers create a changing picture of what your skin is doing now.",
  },
  {
    title: "Build the profile",
    text: "Goals, sensitivities, routine habits, cycle context, weather, and location become part of the recommendation context.",
  },
  {
    title: "Capture the regimen",
    text: "Take photos, scan a barcode, or search products so Blueskies can identify products, ingredients, compounds, and formulas.",
  },
  {
    title: "Track what changed",
    text: "Daily check-ins connect skin feel, visible changes, product use, hormones, and environment over time.",
  },
];

const intelligenceCards = [
  "Barcode and product scan",
  "Ingredient explanation",
  "Personalized fit analysis",
  "Regimen-level cautions",
  "Product effect tracking",
  "Routine recommendations",
];

const platformLayers = [
  {
    title: "Consumer wedge",
    text: "A simple app for tracking skin, scanning products, and understanding what belongs in a routine.",
  },
  {
    title: "Structured data layer",
    text: "Profiles, check-ins, routines, ingredients, compounds, formulations, and constraints become organized skincare context.",
  },
  {
    title: "Intelligence layer",
    text: "Journal-backed evidence and longitudinal outcomes help rank products based on science and the person using them.",
  },
];

export default function Home() {
  return (
    <main className="shell landing-shell">
      <nav className="topbar landing-topbar">
        <div className="brand">
          <Link href="/">Blueskies</Link>
        </div>
        <div className="topbar-actions landing-nav">
          <a href="#how-it-works">How it works</a>
          <a href="#science">Science + you</a>
          <Link href="/experience">Prototype</Link>
          <a href="#contact">Contact us</a>
        </div>
      </nav>

      <section className="landing-hero">
        <div className="landing-hero-copy">
          <p className="landing-eyebrow">Early access roadmap</p>
          <h1>Skincare intelligence based on science and based on you.</h1>
          <p className="landing-lede">
            Blueskies is being built to help people track their skin in one
            place, understand their regimen, scan products, and connect changes
            to ingredients, hormones, weather, location, and product history.
          </p>
          <div className="landing-actions">
            <a className="primary-button link-button" href="#contact">
              Contact us
            </a>
            <a className="secondary-button" href="#how-it-works">
              See how it works
            </a>
          </div>
        </div>

        <div className="landing-preview" aria-label="Blueskies app preview">
          <div className="phone-frame">
            <div className="phone-status">
              <span>Today</span>
              <strong>Skin profile</strong>
            </div>
            <div className="scan-card">
              <div className="face-preview">
                <span className="face-zone face-zone-forehead" />
                <span className="face-zone face-zone-cheek" />
                <span className="face-zone face-zone-chin" />
              </div>
              <div>
                <strong>Analysis preview</strong>
                <p>Redness down 12% after barrier routine</p>
              </div>
            </div>
            <div className="mini-chart" aria-hidden="true">
              <span style={{ height: "48%" }} />
              <span style={{ height: "72%" }} />
              <span style={{ height: "56%" }} />
              <span style={{ height: "84%" }} />
              <span style={{ height: "68%" }} />
              <span style={{ height: "92%" }} />
            </div>
            <div className="product-scan-card">
              <div className="barcode-lines" aria-hidden="true">
                <span />
                <span />
                <span />
                <span />
                <span />
              </div>
              <div>
                <strong>Product scan</strong>
                <p>Niacinamide serum fits current goals</p>
              </div>
            </div>
            <div className="constraint-row">
              <span>Fragrance sensitivity</span>
              <strong>Warn</strong>
            </div>
          </div>

          <div className="floating-panel floating-panel-top">
            <span className="panel-kicker">Journal signal</span>
            <strong>Evidence linked to ingredient role</strong>
          </div>
          <div className="floating-panel floating-panel-bottom">
            <span className="panel-kicker">Context</span>
            <strong>Weather, cycle, routine, skin state</strong>
          </div>
        </div>
      </section>

      <section className="landing-section" id="how-it-works">
        <div className="section-heading">
          <p className="landing-eyebrow">How it works</p>
          <h2>From skin analysis to regimen insight.</h2>
          <p>
            The roadmap is a clear loop: understand the skin, identify the
            products, track changes, and explain what may be helping or hurting.
          </p>
        </div>
        <div className="workflow-grid">
          {workflowSteps.map((step, index) => (
            <article className="workflow-card" key={step.title}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section science-section" id="science">
        <div className="science-copy">
          <p className="landing-eyebrow">Science + you</p>
          <h2>Ingredient research gets personal context.</h2>
          <p>
            Blueskies is designed to look at compounds, formulations, ingredient
            roles, and journal literature, then weigh that evidence against
            your changing profile, sensitivities, regimen, and skin history.
          </p>
        </div>
        <div className="science-panel">
          <div className="evidence-row">
            <span>Journal articles</span>
            <strong>Evidence strength</strong>
          </div>
          <div className="evidence-row">
            <span>Ingredient classes</span>
            <strong>Compound matching</strong>
          </div>
          <div className="evidence-row">
            <span>Your context</span>
            <strong>Personal constraints</strong>
          </div>
          <p>
            Built to support better skincare decisions, not diagnose or treat
            medical conditions.
          </p>
        </div>
      </section>

      <section className="landing-section">
        <div className="section-heading">
          <p className="landing-eyebrow">Regimen intelligence</p>
          <h2>Know what a product is and how it works for you.</h2>
        </div>
        <div className="intelligence-grid">
          {intelligenceCards.map((item) => (
            <article className="intelligence-card" key={item}>
              <div className="intelligence-icon" aria-hidden="true" />
              <h3>{item}</h3>
              <p>
                Preview capability for connecting product identity, ingredient
                science, and personal fit in one place.
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section platform-section">
        <div className="section-heading">
          <p className="landing-eyebrow">Platform vision</p>
          <h2>A consumer app with a deeper skincare intelligence layer.</h2>
        </div>
        <div className="platform-grid">
          {platformLayers.map((layer) => (
            <article className="platform-card" key={layer.title}>
              <h3>{layer.title}</h3>
              <p>{layer.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="contact-section" id="contact">
        <div>
          <p className="landing-eyebrow">Contact us</p>
          <h2>Tell us what you want Blueskies to help with.</h2>
          <p>
            Send your name, email, and feedback. We will reach out shortly as
            we shape the first consumer experience around skin tracking,
            regimen capture, product scans, and science-backed personalization.
          </p>
        </div>
        <ContactForm />
      </section>

      <footer className="landing-footer">
        <span>Blueskies roadmap preview</span>
        <div>
          <Link href="/experience">Prototype</Link>
          <Link href="/compounds">Compounds</Link>
          <Link href="/skincareApi">Catalog</Link>
        </div>
      </footer>
    </main>
  );
}

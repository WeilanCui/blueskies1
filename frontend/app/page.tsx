import Link from "next/link";

import ContactForm from "./ContactForm";
import styles from "./page.module.css";

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
    <main className={["shell", styles.landingShell].join(" ")}>
      <nav className={["topbar", styles.landingTopbar].join(" ")}>
        <div className="brand">
          <Link href="/">Blueskies</Link>
        </div>
        <div className={["topbar-actions", styles.landingNav].join(" ")}>
          <a href="#how-it-works">How it works</a>
          <a href="#science">Science + you</a>
          <Link href="/login">Log in</Link>
          <a href="#contact">Contact us</a>
        </div>
      </nav>

      <section className={styles.landingHero}>
        <div className={styles.landingHeroCopy}>
          <p className="landing-eyebrow">Early access roadmap</p>
          <h1>Skincare intelligence based on science and based on you.</h1>
          <p className={styles.landingLede}>
            Blueskies is being built to help people track their skin in one
            place, understand their regimen, scan products, and connect changes
            to ingredients, hormones, weather, location, and product history.
          </p>
          <div className={styles.landingActions}>
            <Link className="primary-button link-button" href="/login">
              Start intake
            </Link>
            <a className={styles.secondaryButton} href="#how-it-works">
              See how it works
            </a>
          </div>
        </div>

        <section
          className={styles.landingPreview}
          aria-label="Blueskies app preview"
        >
          <div className={styles.phoneFrame}>
            <div className={styles.phoneStatus}>
              <span>Today</span>
              <strong>Skin profile</strong>
            </div>
            <div className={styles.scanCard}>
              <div className={styles.facePreview}>
                <span
                  className={[styles.faceZone, styles.faceZoneForehead].join(
                    " ",
                  )}
                />
                <span
                  className={[styles.faceZone, styles.faceZoneCheek].join(" ")}
                />
                <span
                  className={[styles.faceZone, styles.faceZoneChin].join(" ")}
                />
              </div>
              <div>
                <strong>Analysis preview</strong>
                <p>Redness down 12% after barrier routine</p>
              </div>
            </div>
            <div className={styles.miniChart} aria-hidden="true">
              <span className={styles.chartBar1} />
              <span className={styles.chartBar2} />
              <span className={styles.chartBar3} />
              <span className={styles.chartBar4} />
              <span className={styles.chartBar5} />
              <span className={styles.chartBar6} />
            </div>
            <div className={styles.productScanCard}>
              <div className={styles.barcodeLines} aria-hidden="true">
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
            <div className={styles.constraintRow}>
              <span>Fragrance sensitivity</span>
              <strong>Warn</strong>
            </div>
          </div>

          <div
            className={[styles.floatingPanel, styles.floatingPanelTop].join(
              " ",
            )}
          >
            <span className={styles.panelKicker}>Journal signal</span>
            <strong>Evidence linked to ingredient role</strong>
          </div>
          <div
            className={[styles.floatingPanel, styles.floatingPanelBottom].join(
              " ",
            )}
          >
            <span className={styles.panelKicker}>Context</span>
            <strong>Weather, cycle, routine, skin state</strong>
          </div>
        </section>
      </section>

      <section className={styles.landingSection} id="how-it-works">
        <div className={styles.sectionHeading}>
          <p className="landing-eyebrow">How it works</p>
          <h2>From skin analysis to regimen insight.</h2>
          <p>
            The roadmap is a clear loop: understand the skin, identify the
            products, track changes, and explain what may be helping or hurting.
          </p>
        </div>
        <div className={styles.workflowGrid}>
          {workflowSteps.map((step, index) => (
            <article className={styles.workflowCard} key={step.title}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section
        className={[styles.landingSection, styles.scienceSection].join(" ")}
        id="science"
      >
        <div className={styles.scienceCopy}>
          <p className="landing-eyebrow">Science + you</p>
          <h2>Ingredient research gets personal context.</h2>
          <p>
            Blueskies is designed to look at compounds, formulations, ingredient
            roles, and journal literature, then weigh that evidence against your
            changing profile, sensitivities, regimen, and skin history.
          </p>
        </div>
        <div className={styles.sciencePanel}>
          <div className={styles.evidenceRow}>
            <span>Journal articles</span>
            <strong>Evidence strength</strong>
          </div>
          <div className={styles.evidenceRow}>
            <span>Ingredient classes</span>
            <strong>Compound matching</strong>
          </div>
          <div className={styles.evidenceRow}>
            <span>Your context</span>
            <strong>Personal constraints</strong>
          </div>
          <p>
            Built to support better skincare decisions, not diagnose or treat
            medical conditions.
          </p>
        </div>
      </section>

      <section className={styles.landingSection}>
        <div className={styles.sectionHeading}>
          <p className="landing-eyebrow">Regimen intelligence</p>
          <h2>Know what a product is and how it works for you.</h2>
        </div>
        <div className={styles.intelligenceGrid}>
          {intelligenceCards.map((item) => (
            <article className={styles.intelligenceCard} key={item}>
              <div className={styles.intelligenceIcon} aria-hidden="true" />
              <h3>{item}</h3>
              <p>
                Preview capability for connecting product identity, ingredient
                science, and personal fit in one place.
              </p>
            </article>
          ))}
        </div>
      </section>

      <section
        className={[styles.landingSection, styles.platformSection].join(" ")}
      >
        <div className={styles.sectionHeading}>
          <p className="landing-eyebrow">Platform vision</p>
          <h2>A consumer app with a deeper skincare intelligence layer.</h2>
        </div>
        <div className={styles.platformGrid}>
          {platformLayers.map((layer) => (
            <article className={styles.platformCard} key={layer.title}>
              <h3>{layer.title}</h3>
              <p>{layer.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.contactSection} id="contact">
        <div>
          <p className="landing-eyebrow">Contact us</p>
          <h2>Tell us what you want Blueskies to help with.</h2>
          <p>
            Send your name, email, and feedback. We will reach out shortly as we
            shape the first consumer experience around skin tracking, regimen
            capture, product scans, and science-backed personalization.
          </p>
        </div>
        <ContactForm />
      </section>

      <footer className={styles.landingFooter}>
        <span>Blueskies roadmap preview</span>
        <div>
          <Link href="/login">Log in</Link>
          <Link href="/compounds">Compounds</Link>
          <Link href="/skincareApi">Catalog</Link>
        </div>
      </footer>
    </main>
  );
}

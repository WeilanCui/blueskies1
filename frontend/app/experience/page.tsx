import Link from "next/link";
import ExperienceFlow from "./ExperienceFlow";

export default function ExperiencePage() {
  return (
    <main className="shell experience-shell">
      <nav className="topbar">
        <div className="brand">
          <Link href="/">Blueskies</Link>
        </div>
        <div className="topbar-actions">
          <Link className="nav-button" href="/">
            Submit product
          </Link>
          <Link className="nav-button" href="/compounds">
            Browse compounds
          </Link>
        </div>
      </nav>

      <section className="experience-hero">
        <p className="experience-eyebrow">Personalized skincare intelligence</p>
        <h1 className="page-title">From facial scan to routine recommendations</h1>
        <p className="lede">
          Blueskies analyzes your face, captures your skin profile and
          sensitivities, researches the ingredients in your current products,
          and recommends what to use next.
        </p>
      </section>

      <ExperienceFlow />
    </main>
  );
}

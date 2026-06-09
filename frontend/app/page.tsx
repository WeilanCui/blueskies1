import Link from "next/link";

import { getServerApiBaseUrl } from "../lib/apiBaseUrl";
import ProductSubmitForm from "./ProductSubmitForm";

async function getHealth() {
  try {
    const response = await fetch(`${getServerApiBaseUrl()}/api/health/`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });

    if (!response.ok) {
      return { status: "error", upstreamStatus: response.status };
    }

    return response.json();
  } catch {
    return { status: "starting" };
  }
}

export default async function Home() {
  const health = await getHealth();

  return (
    <main className="shell">
      <nav className="topbar">
        <div className="brand">Blueskies</div>
        <div className="topbar-actions">
          <Link className="nav-button" href="/experience">
            Personalized experience
          </Link>
          <Link href="/compounds">Browse compounds</Link>
          <Link href="/skincareApi">Skincare catalog</Link>
          <div className="status" aria-label="Backend status">
            <span className="status-dot" />
            <span>{health.status ?? "unknown"}</span>
          </div>
        </div>
      </nav>

      <section className="page-head">
        <h1 className="page-title">Submit a product</h1>
        <p className="lede">
          Enter a product name and its INCI formulation. Blueskies will parse
          each ingredient, enrich it from INCI and PubChem/PubMed, and store
          the compound data for review.
        </p>
        <div className="home-cta">
          <Link className="primary-button link-button" href="/experience">
            Start personalized experience
          </Link>
        </div>
      </section>

      <ProductSubmitForm />
    </main>
  );
}

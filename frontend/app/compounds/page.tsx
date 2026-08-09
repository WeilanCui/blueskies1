import Link from "next/link";
import { Suspense } from "react";
import { Panel } from "../../components/Panel";
import { getServerApiBaseUrl } from "../../lib/apiBaseUrl";
import CompoundList, { type Compound } from "./CompoundList";
import styles from "./compounds.module.css";

async function getCompounds(): Promise<{
  compounds: Compound[];
  error: boolean;
}> {
  const baseUrl = getServerApiBaseUrl();

  try {
    const response = await fetch(`${baseUrl}/api/compounds/`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return { compounds: [], error: true };
    }

    const data = (await response.json()) as Compound[];
    return { compounds: data, error: false };
  } catch {
    return { compounds: [], error: true };
  }
}

export default async function CompoundsPage() {
  const { compounds, error } = await getCompounds();

  return (
    <main className="shell">
      <nav className="topbar">
        <div className="brand">
          <Link href="/">Blueskies</Link>
        </div>
        <div className="topbar-actions">
          <Link className="nav-button" href="/login">
            Start intake
          </Link>
          <Link className="nav-button" href="/skincareApi">
            Skincare catalog
          </Link>
          <span>{compounds.length} compounds</span>
        </div>
      </nav>

      <section className={styles.pageHead}>
        <h1 className={styles.pageTitle}>Compounds</h1>
        <p className="lede">
          Browse ingredients in the database. Select a compound to expand its
          identifiers, structure, properties, and literature.
        </p>
      </section>

      {error ? (
        <Panel as="div" variant="notice" error>
          Could not reach the backend API. Make sure the Django service is
          running on port 8000.
        </Panel>
      ) : compounds.length === 0 ? (
        <Panel as="div" variant="notice">
          No compounds found yet. Seed or ingest data first, e.g.{" "}
          <code>
            docker compose run --rm backend python manage.py ingest_compound
          </code>
          .
        </Panel>
      ) : (
        <Suspense fallback={<p className="detail-muted">Loading compounds…</p>}>
          <CompoundList compounds={compounds} />
        </Suspense>
      )}
    </main>
  );
}

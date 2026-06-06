import Link from "next/link";
import CompoundList, { type Compound } from "./CompoundList";

async function getCompounds(): Promise<{ compounds: Compound[]; error: boolean }> {
  const baseUrl = process.env.SERVER_API_BASE_URL ?? "http://backend:8000";

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
        <div className="status">
          <span>{compounds.length} compounds</span>
        </div>
      </nav>

      <section className="page-head">
        <h1 className="page-title">Compounds</h1>
        <p className="lede">
          Browse ingredients in the database. Select a compound to expand its
          identifiers, structure, properties, and literature.
        </p>
      </section>

      {error ? (
        <div className="notice notice-error">
          Could not reach the backend API. Make sure the Django service is
          running on port 8000.
        </div>
      ) : compounds.length === 0 ? (
        <div className="notice">
          No compounds found yet. Seed or ingest data first, e.g.{" "}
          <code>docker compose run --rm backend python manage.py ingest_compound</code>.
        </div>
      ) : (
        <CompoundList compounds={compounds} />
      )}
    </main>
  );
}

import Link from "next/link";
import { Panel } from "../../components/Panel";
import { getServerApiBaseUrl } from "../../lib/apiBaseUrl";
import SkincareCatalog from "./SkincareCatalog";
import styles from "./skincareApi.module.css";
import type { ProductSearchResponse, SkincareProduct } from "./types";

const INITIAL_PAGE_SIZE = 25;

async function getInitialProducts(): Promise<{
  products: SkincareProduct[];
  error: boolean;
}> {
  const baseUrl = getServerApiBaseUrl();

  try {
    const response = await fetch(
      `${baseUrl}/api/products/search/?limit=${INITIAL_PAGE_SIZE}`,
      {
        cache: "no-store",
        signal: AbortSignal.timeout(8000),
      },
    );

    if (!response.ok) {
      return { products: [], error: true };
    }

    const data = (await response.json()) as ProductSearchResponse;
    return { products: data.results, error: false };
  } catch {
    return { products: [], error: true };
  }
}

export default async function SkincareApiPage() {
  const { products, error } = await getInitialProducts();

  return (
    <main className="shell">
      <nav className="topbar">
        <div className="brand">
          <Link href="/">Blueskies</Link>
        </div>
        <div className="topbar-actions">
          <Link className="nav-button" href="/compounds">
            Compounds
          </Link>
          <Link className="nav-button" href="/login">
            Start intake
          </Link>
        </div>
      </nav>

      <section className={styles.pageHead}>
        <h1 className={styles.pageTitle}>Skincare catalog</h1>
        <p className="lede">
          Browse and search the Blueskies product catalog and its resolved
          ingredients. The frontend talks to <code>/api/skincareApi/*</code>,
          which proxies the Django catalog endpoints.
        </p>
      </section>

      {error ? (
        <Panel as="div" variant="notice" error>
          Could not reach the catalog API. If the backend is up, its catalog may
          not be seeded yet — run <code>seed_catalog</code> to populate it.
        </Panel>
      ) : null}

      <SkincareCatalog initialProducts={products} initialError={error} />
    </main>
  );
}

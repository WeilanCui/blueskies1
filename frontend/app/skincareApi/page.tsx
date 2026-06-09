import Link from "next/link";

import { getServerApiBaseUrl } from "../../lib/apiBaseUrl";
import { Panel } from "../../components/Panel";
import SkincareCatalog from "./SkincareCatalog";
import type { SkincareProduct } from "./types";

async function getInitialProducts(): Promise<{
  products: SkincareProduct[];
  error: boolean;
}> {
  const baseUrl = getServerApiBaseUrl();

  try {
    const response = await fetch(`${baseUrl}/api/skincare/products/`, {
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });

    if (!response.ok) {
      return { products: [], error: true };
    }

    const data = (await response.json()) as SkincareProduct[];
    return { products: data, error: false };
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
          <Link className="nav-button" href="/experience">
            Personalized experience
          </Link>
        </div>
      </nav>

      <section className="page-head">
        <h1 className="page-title">Skincare catalog</h1>
        <p className="lede">
          Browse and search 2,000+ skincare products via the{" "}
          <a
            href="https://github.com/LauraAddams/skincareAPI"
            target="_blank"
            rel="noreferrer"
          >
            LauraAddams skincareAPI
          </a>
          . The Blueskies backend proxies all requests so the frontend talks to{" "}
          <code>/api/skincareApi/*</code> only.
        </p>
      </section>

      {error ? (
        <Panel as="div" variant="notice" error>
          The upstream Skincare API may be offline (the Heroku deployment has been
          retired). Search and create still route through Django at{" "}
          <code>/api/skincare/</code> and will work when the service is reachable.
        </Panel>
      ) : null}

      <SkincareCatalog initialProducts={products.slice(0, 25)} initialError={error} />
    </main>
  );
}

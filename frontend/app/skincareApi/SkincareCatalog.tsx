"use client";

import { useState } from "react";

import { Panel } from "../../components/Panel";
import type {
  IngredientSearchResponse,
  ProductSearchResponse,
  SkincareIngredient,
  SkincareProduct,
} from "./types";
import styles from "./skincareApi.module.css";

type Tab = "products" | "ingredients";

type SkincareCatalogProps = {
  initialProducts: SkincareProduct[];
  initialError: boolean;
};

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export default function SkincareCatalog({
  initialProducts,
  initialError,
}: SkincareCatalogProps) {
  const [tab, setTab] = useState<Tab>("products");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(10);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(initialError ? "Could not load catalog." : "");
  const [products, setProducts] = useState<SkincareProduct[]>(initialProducts);
  const [ingredients, setIngredients] = useState<SkincareIngredient[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<SkincareProduct | null>(null);
  const [searchMeta, setSearchMeta] = useState<{ count: number; query: string } | null>(
    null,
  );
  const [createForm, setCreateForm] = useState({
    brand: "",
    name: "",
    ingredients: "",
  });
  const [createMessage, setCreateMessage] = useState("");

  async function loadAllProducts() {
    setLoading(true);
    setError("");
    setSearchMeta(null);
    setSelectedProduct(null);

    try {
      const response = await fetch("/api/skincareApi/products");
      if (!response.ok) {
        const payload = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(payload.detail ?? `Request failed (${response.status})`);
      }
      const data = (await response.json()) as SkincareProduct[];
      setProducts(data);
      setTab("products");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load products.");
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }

  async function runSearch() {
    const trimmed = query.trim();
    if (!trimmed) {
      setError("Enter a search term.");
      return;
    }

    setLoading(true);
    setError("");
    setSelectedProduct(null);

    const params = new URLSearchParams({
      q: trimmed,
      limit: String(limit),
      page: String(page),
    });

    const endpoint =
      tab === "products"
        ? `/api/skincareApi/products/search?${params}`
        : `/api/skincareApi/ingredients/search?${params}`;

    try {
      const response = await fetch(endpoint);
      if (!response.ok) {
        const payload = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(payload.detail ?? `Search failed (${response.status})`);
      }

      if (tab === "products") {
        const data = (await response.json()) as ProductSearchResponse;
        setProducts(data.results);
        setIngredients([]);
        setSearchMeta({ count: data.count, query: data.query });
      } else {
        const data = (await response.json()) as IngredientSearchResponse;
        setIngredients(data.results);
        setProducts([]);
        setSearchMeta({ count: data.count, query: data.query });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  async function loadProductDetail(productId: number) {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`/api/skincareApi/products/${productId}`);
      if (!response.ok) {
        const payload = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(payload.detail ?? `Product not found (${response.status})`);
      }
      const data = (await response.json()) as SkincareProduct;
      setSelectedProduct(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load product.");
    } finally {
      setLoading(false);
    }
  }

  async function createProduct(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setCreateMessage("");
    setError("");

    try {
      const response = await fetch("/api/skincareApi/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(createForm),
      });
      const data = (await response.json()) as SkincareProduct & { detail?: string };
      if (!response.ok) {
        throw new Error(data.detail ?? `Create failed (${response.status})`);
      }
      setCreateMessage(`Added product #${data.id}: ${data.brand} — ${data.name}`);
      setCreateForm({ brand: "", name: "", ingredients: "" });
      setProducts((current) => [data, ...current]);
      setSelectedProduct(data);
      setTab("products");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create product.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="stack">
      <Panel as="section" variant="form">
        <div className="stack">
          <div className="topbar-actions">
            <button
              type="button"
              className={cx(
                "nav-button",
                tab === "products" && styles.navButtonActive,
              )}
              onClick={() => setTab("products")}
            >
              Products
            </button>
            <button
              type="button"
              className={cx(
                "nav-button",
                tab === "ingredients" && styles.navButtonActive,
              )}
              onClick={() => setTab("ingredients")}
            >
              Ingredients
            </button>
          </div>

          <div className={styles.fieldRow}>
            <label className="field">
              <span>Search</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={tab === "products" ? "brand, product, or ingredient" : "ingredient name"}
              />
            </label>
            <label className={cx("field", styles.fieldCompact)}>
              <span>Limit</span>
              <input
                type="number"
                min={1}
                max={100}
                value={limit}
                onChange={(event) => setLimit(Number(event.target.value) || 10)}
              />
            </label>
            <label className={cx("field", styles.fieldCompact)}>
              <span>Page</span>
              <input
                type="number"
                min={1}
                value={page}
                onChange={(event) => setPage(Number(event.target.value) || 1)}
              />
            </label>
          </div>

          <div className="topbar-actions">
            <button
              type="button"
              className={styles.actionButton}
              onClick={runSearch}
              disabled={loading}
            >
              {loading ? "Loading…" : "Search"}
            </button>
            {tab === "products" ? (
              <button
                type="button"
                className="nav-button"
                onClick={loadAllProducts}
                disabled={loading}
              >
                Load all products
              </button>
            ) : null}
          </div>
        </div>
      </Panel>

      {error ? (
        <Panel as="div" variant="notice" error>
          {error}
        </Panel>
      ) : null}

      {searchMeta ? (
        <p className="lede">
          {searchMeta.count} result{searchMeta.count === 1 ? "" : "s"} for “{searchMeta.query}”
        </p>
      ) : null}

      {tab === "products" ? (
        <Panel as="section" variant="results">
          {products.length === 0 ? (
            <p>No products to show. Try search or load the full catalog.</p>
          ) : (
            <ul className={styles.catalogList}>
              {products.map((product) => (
                <li key={product.id}>
                  <button
                    type="button"
                    className={styles.catalogCard}
                    onClick={() => loadProductDetail(product.id)}
                  >
                    <strong>{product.brand}</strong>
                    <span>{product.name}</span>
                    <small>{product.ingredient_list.length} ingredients</small>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      ) : (
        <Panel as="section" variant="results">
          {ingredients.length === 0 ? (
            <p>No ingredients to show. Run a search to populate results.</p>
          ) : (
            <ul className={styles.catalogList}>
              {ingredients.map((ingredient) => (
                <li key={ingredient.id} className={styles.catalogCard}>
                  <span>{ingredient.ingredient}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )}

      {selectedProduct ? (
        <Panel as="section" variant="default">
          <h2 className={styles.pageTitle}>
            {selectedProduct.brand} — {selectedProduct.name}
          </h2>
          <p className="lede">Product #{selectedProduct.id}</p>
          <ul className={styles.propertyList}>
            {selectedProduct.ingredient_list.map((ingredient) => (
              <li key={ingredient}>{ingredient}</li>
            ))}
          </ul>
        </Panel>
      ) : null}

      <Panel as="section" variant="form">
        <h2 className={styles.pageTitle}>Add product</h2>
        <form className="stack" onSubmit={createProduct}>
          <label className="field">
            <span>Brand</span>
            <input
              required
              value={createForm.brand}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, brand: event.target.value }))
              }
            />
          </label>
          <label className="field">
            <span>Name</span>
            <input
              required
              value={createForm.name}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, name: event.target.value }))
              }
            />
          </label>
          <label className="field">
            <span>Ingredients (comma-separated)</span>
            <textarea
              required
              rows={4}
              value={createForm.ingredients}
              onChange={(event) =>
                setCreateForm((current) => ({
                  ...current,
                  ingredients: event.target.value,
                }))
              }
              placeholder="water,glycerin,citric acid"
            />
          </label>
          <button type="submit" className={styles.actionButton} disabled={loading}>
            {loading ? "Saving…" : "Create product"}
          </button>
          {createMessage ? <p className="lede">{createMessage}</p> : null}
        </form>
      </Panel>
    </div>
  );
}

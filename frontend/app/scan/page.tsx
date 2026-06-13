"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Button } from "../../components/Button";
import { getCatalogProducts, getMe, type CatalogProduct } from "../../lib/appApi";
import styles from "./scan.module.css";

const authFreshMs = 5 * 60 * 1000;

function categorySwatch(category: string): string {
  const swatches: Record<string, string> = {
    Moisturizer: "cream",
    Serum: "serum",
    SPF: "spf",
    Cleanser: "cleanser",
    Treatment: "treatment",
    Toner: "toner",
  };
  return swatches[category] ?? "cream";
}

function analysisCounts(ingredients: CatalogProduct["ingredients"]) {
  const beneficial = ingredients.filter(
    (ingredient) => ingredient.is_key_active || ingredient.note.trim(),
  ).length;
  const caution = ingredients.filter(
    (ingredient) => ingredient.parse_status === "unmatched",
  ).length;
  return { beneficial, caution };
}

function formatEnrichmentStatus(status: string): string {
  if (!status) {
    return "Pending analysis";
  }
  return status.replaceAll("_", " ");
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ScanPage() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
    staleTime: authFreshMs,
  });
  const productsQuery = useQuery({
    queryKey: ["catalog-products"],
    queryFn: () => getCatalogProducts(),
    enabled: meQuery.isSuccess,
    staleTime: authFreshMs,
  });
  useEffect(() => {
    if (meQuery.isError) {
      router.replace("/login");
    }
  }, [meQuery.isError, router]);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  function selectImage(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    event.target.value = "";
  }

  const products = productsQuery.data ?? [];
  const filteredProducts = useMemo(() => {
    const needle = searchQuery.trim().toLowerCase();
    if (!needle) {
      return products;
    }
    return products.filter((product) =>
      [product.brand, product.name, product.category, product.description].some(
        (value) => value.toLowerCase().includes(needle),
      ),
    );
  }, [products, searchQuery]);

  const selectedProduct = products.find((product) => product.id === selectedProductId);
  const selectedAnalysis = selectedProduct
    ? analysisCounts(selectedProduct.ingredients)
    : null;

  if (meQuery.isLoading || meQuery.isError) {
    return <p className="detail-muted">Loading your session...</p>;
  }

  return (
    <>
      <div className={styles.scanLayout}>
        {selectedProduct ? (
          <section className={styles.productDetail}>
            <button
              className={styles.backButton}
              type="button"
              onClick={() => setSelectedProductId(null)}
            >
              <span aria-hidden="true" />
              Back
            </button>

            <article className={styles.detailHeroCard}>
              <div
                className={[
                  styles.detailImage,
                  styles[`productImage${categorySwatch(selectedProduct.category)}`],
                ].join(" ")}
                aria-hidden="true"
              >
                <span>{selectedProduct.category}</span>
              </div>
              <div className={styles.detailBody}>
                <div className={styles.detailTitleRow}>
                  <div>
                    <span>{selectedProduct.brand}</span>
                    <h1>{selectedProduct.name}</h1>
                  </div>
                  <strong>{selectedProduct.category}</strong>
                </div>
                <div className={styles.detailMeta}>
                  <span>{formatEnrichmentStatus(selectedProduct.enrichment_status)}</span>
                  <span>{selectedProduct.ingredient_count} ingredients</span>
                </div>
                <p>{selectedProduct.description}</p>
                <Button className={styles.addedButton} type="button" variant="secondary">
                  <span aria-hidden="true">✓</span>
                  Added to routine
                </Button>
              </div>
            </article>

            <section className={styles.analysisSection}>
              <h2>Ingredient Analysis</h2>
              {selectedAnalysis &&
              (selectedAnalysis.beneficial > 0 || selectedAnalysis.caution > 0) ? (
                <div className={styles.analysisSummary}>
                  {selectedAnalysis.beneficial > 0 ? (
                    <span className={styles.beneficialBadge}>
                      {selectedAnalysis.beneficial} beneficial
                    </span>
                  ) : null}
                  {selectedAnalysis.caution > 0 ? (
                    <span className={styles.cautionBadge}>
                      {selectedAnalysis.caution} caution
                    </span>
                  ) : null}
                </div>
              ) : null}
              <div className={styles.ingredientList}>
                {selectedProduct.ingredients.map((ingredient, index) => (
                  <article
                    className={styles.ingredientCard}
                    key={`${ingredient.name}-${index}`}
                  >
                    <span className={styles.shieldIcon} aria-hidden="true" />
                    <div>
                      <div className={styles.ingredientTitleRow}>
                        <h3>{ingredient.name}</h3>
                        <strong>{ingredient.role}</strong>
                      </div>
                      {ingredient.note ? <p>{ingredient.note}</p> : null}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </section>
        ) : (
          <>
            <section className={styles.scanHero}>
              <h1>Products</h1>
              <p>Search or scan to analyze ingredients.</p>
            </section>

            <section className={styles.searchRow} aria-label="Product search and scan">
              <label className={styles.searchField}>
                <span className={styles.searchIcon} aria-hidden="true" />
                <input
                  type="search"
                  placeholder="Search products, brands..."
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
              </label>
              <label className={styles.scanButton}>
                <span className={styles.cameraIcon} aria-hidden="true" />
                <span>Scan</span>
                <input
                  accept="image/*"
                  capture="environment"
                  className={styles.fileInput}
                  onChange={selectImage}
                  type="file"
                />
              </label>
            </section>

            {selectedFile && (
              <section className={styles.uploadPanel}>
                <div className={styles.uploadPreview}>
                  {previewUrl ? <img alt="Selected scan preview" src={previewUrl} /> : null}
                </div>
                <div>
                  <strong>{selectedFile.name}</strong>
                  <span>{formatBytes(selectedFile.size)}</span>
                  <p>
                    This preview stays on your device in this pass. No image is
                    sent to the backend yet.
                  </p>
                </div>
              </section>
            )}

            <section className={styles.productList} aria-label="Product catalog">
              {productsQuery.isLoading ? (
                <p className="detail-muted">Loading products...</p>
              ) : productsQuery.isError ? (
                <p className="detail-muted">
                  Could not load the product catalog. Check that the backend is running.
                </p>
              ) : filteredProducts.length === 0 ? (
                <p className="detail-muted">
                  {products.length === 0
                    ? "No products in the catalog yet. Run `python manage.py seed_catalog` on the backend."
                    : "No products match your search."}
                </p>
              ) : (
                filteredProducts.map((product) => (
                  <button
                    className={styles.productCard}
                    key={product.id}
                    type="button"
                    onClick={() => setSelectedProductId(product.id)}
                  >
                    <div
                      className={[
                        styles.productImage,
                        styles[`productImage${categorySwatch(product.category)}`],
                      ].join(" ")}
                      aria-hidden="true"
                    >
                      <span>{product.category}</span>
                    </div>
                    <div className={styles.productInfo}>
                      <span>{product.brand}</span>
                      <h2>{product.name}</h2>
                      <div className={styles.productMeta}>
                        <strong>{product.category}</strong>
                        <em>{product.ingredient_count} ingredients</em>
                      </div>
                    </div>
                    <span className={styles.checkMark} aria-hidden="true" />
                  </button>
                ))
              )}
            </section>

            <section className={styles.uploadActions}>
              <label className={styles.secondaryUpload}>
                Upload product photo
                <input
                  accept="image/*"
                  className={styles.fileInput}
                  onChange={selectImage}
                  type="file"
                />
              </label>
              <label className={styles.secondaryUpload}>
                Upload skin photo
                <input
                  accept="image/*"
                  className={styles.fileInput}
                  onChange={selectImage}
                  type="file"
                />
              </label>
            </section>

            <section className={styles.scanPanel}>
              <div className={styles.scanActions}>
                <label className={styles.fileAction}>
                  Take another photo
                  <input
                    accept="image/*"
                    capture="environment"
                    className={styles.fileInput}
                    onChange={selectImage}
                    type="file"
                  />
                </label>
                <label className={[styles.fileAction, styles.fileActionSecondary].join(" ")}>
                  Upload photo
                  <input
                    accept="image/*"
                    className={styles.fileInput}
                    onChange={selectImage}
                    type="file"
                  />
                </label>
                <p className={styles.scanNote}>
                  Product lookup is connected to the catalog. Image scan upload stays
                  on your device for now.
                </p>
              </div>
            </section>
          </>
        )}
      </div>

    </>
  );
}

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "../../components/Button";
import {
  addProductToRoutine,
  getCatalogProducts,
  getMe,
  getRoutines,
  type CatalogProduct,
  type Routine,
  type RoutineTimeOfDay,
} from "../../lib/appApi";
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

function displayRoutineName(routine: Routine): string {
  if (routine.time_of_day === "custom") {
    return routine.custom_time_label || routine.name;
  }
  if (routine.time_of_day === "am") {
    return "AM Routine";
  }
  if (routine.time_of_day === "pm") {
    return "PM Routine";
  }
  return routine.name;
}

type RoutineTarget = {
  value: string;
  label: string;
  timeOfDay: RoutineTimeOfDay;
  customTimeLabel?: string;
  routine?: Routine;
};

function routineValue(routine: Routine): string {
  return `routine:${routine.id}`;
}

function routineHasProduct(routine: Routine | undefined, product: CatalogProduct | null): boolean {
  if (!routine || !product) {
    return false;
  }
  return routine.items.some(
    (item) =>
      item.product_id === product.product_id ||
      (product.formulation_id !== null && item.formulation_id === product.formulation_id),
  );
}

export default function ScanPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [routineTarget, setRoutineTarget] = useState("am");
  const [routineMessage, setRoutineMessage] = useState<string | null>(null);
  const preserveRoutineMessageRef = useRef(false);

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
  const routinesQuery = useQuery({
    queryKey: ["routines", "active"],
    queryFn: () => getRoutines(true),
    enabled: meQuery.isSuccess,
  });
  const addToRoutineMutation = useMutation({
    mutationFn: addProductToRoutine,
    onSuccess: (data) => {
      const routineName = displayRoutineName(data.routine);
      preserveRoutineMessageRef.current = true;
      setRoutineTarget(routineValue(data.routine));
      setRoutineMessage(
        data.created ? `Added to ${routineName}.` : `Already in ${routineName}.`,
      );
      queryClient.invalidateQueries({ queryKey: ["routines"] });
    },
    onError: (error) => {
      setRoutineMessage(
        error instanceof Error ? error.message : "Could not add product to routine.",
      );
    },
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
  const routines = routinesQuery.data ?? [];
  const routineTargets = useMemo(() => {
    const amRoutine = routines.find((routine) => routine.time_of_day === "am");
    const pmRoutine = routines.find((routine) => routine.time_of_day === "pm");
    const targets: RoutineTarget[] = [
      {
        value: amRoutine ? routineValue(amRoutine) : "am",
        label: "AM Routine",
        timeOfDay: "am",
        routine: amRoutine,
      },
      {
        value: pmRoutine ? routineValue(pmRoutine) : "pm",
        label: "PM Routine",
        timeOfDay: "pm",
        routine: pmRoutine,
      },
    ];
    routines
      .filter((routine) => routine.time_of_day === "custom")
      .forEach((routine) => {
        targets.push({
          value: routineValue(routine),
          label: displayRoutineName(routine),
          timeOfDay: "custom",
          customTimeLabel: routine.custom_time_label,
          routine,
        });
      });
    return targets;
  }, [routines]);
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
  const selectedRoutineTarget =
    routineTargets.find((target) => target.value === routineTarget) ?? routineTargets[0];
  const selectedProductAlreadyInRoutine = routineHasProduct(
    selectedRoutineTarget?.routine,
    selectedProduct ?? null,
  );

  useEffect(() => {
    if (
      routineTargets.length > 0 &&
      !routineTargets.some((target) => target.value === routineTarget)
    ) {
      setRoutineTarget(routineTargets[0].value);
    }
  }, [routineTarget, routineTargets]);

  useEffect(() => {
    if (preserveRoutineMessageRef.current) {
      preserveRoutineMessageRef.current = false;
      return;
    }
    setRoutineMessage(null);
  }, [selectedProductId, routineTarget]);

  function addSelectedProductToRoutine() {
    if (!selectedProduct || !selectedRoutineTarget) {
      return;
    }
    addToRoutineMutation.mutate({
      routine_id: selectedRoutineTarget.routine?.id ?? null,
      time_of_day: selectedRoutineTarget.timeOfDay,
      custom_time_label: selectedRoutineTarget.customTimeLabel ?? "",
      product_id: selectedProduct.product_id,
      formulation_id: selectedProduct.formulation_id,
    });
  }

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
                <div className={styles.routineAddPanel}>
                  <label className={styles.routineSelectLabel}>
                    <span>Add to</span>
                    <select
                      value={selectedRoutineTarget?.value ?? routineTarget}
                      disabled={routinesQuery.isLoading || addToRoutineMutation.isPending}
                      onChange={(event) => {
                        setRoutineTarget(event.target.value);
                        setRoutineMessage(null);
                      }}
                    >
                      {routineTargets.map((target) => (
                        <option value={target.value} key={target.value}>
                          {target.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <Button
                    className={styles.addedButton}
                    type="button"
                    variant="secondary"
                    isDisabled={
                      routinesQuery.isLoading ||
                      addToRoutineMutation.isPending ||
                      selectedProductAlreadyInRoutine
                    }
                    onPress={addSelectedProductToRoutine}
                  >
                    <span aria-hidden="true">✓</span>
                    {addToRoutineMutation.isPending
                      ? "Adding..."
                      : selectedProductAlreadyInRoutine
                        ? `Already in ${selectedRoutineTarget?.label ?? "routine"}`
                        : "Add to routine"}
                  </Button>
                  {routineMessage ? (
                    <p className={styles.routineStatus}>{routineMessage}</p>
                  ) : null}
                </div>
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

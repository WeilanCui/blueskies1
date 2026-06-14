"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AppPageHeader } from "../../components/AppPageHeader";
import { Button } from "../../components/Button";
import {
  createReaction,
  getCatalogProducts,
  getMe,
  getReactions,
  getRoutines,
  updateReaction,
  type CatalogProduct,
  type ReactionEvent,
  type Routine,
  type RoutineItem,
} from "../../lib/appApi";
import styles from "./reactions.module.css";

const authFreshMs = 5 * 60 * 1000;

type ReactionFormState = {
  title: string;
  product_id: string;
  formulation_id: string;
  routine_id: string;
  routine_item_id: string;
  suspected_trigger: string;
  symptoms: string;
  severity: ReactionEvent["severity"];
  status: ReactionEvent["status"];
  occurred_on: string;
  resolved_on: string;
  notes: string;
};

function todayInputValue(): string {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function initialFormState(): ReactionFormState {
  return {
    title: "",
    product_id: "",
    formulation_id: "",
    routine_id: "",
    routine_item_id: "",
    suspected_trigger: "",
    symptoms: "",
    severity: "mild",
    status: "active",
    occurred_on: todayInputValue(),
    resolved_on: "",
    notes: "",
  };
}

function formatDate(value: string): string {
  if (!value) {
    return "Today";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

function reactionContext(entry: ReactionEvent): string {
  return (
    entry.product?.display_name ||
    entry.product?.name ||
    entry.suspected_trigger ||
    entry.symptoms[0] ||
    "Reaction"
  );
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

function displayRoutineItem(item: RoutineItem): string {
  return (
    item.display_name ||
    item.product?.display_name ||
    item.raw_product_name ||
    item.routine_step
  );
}

function productLabel(product: CatalogProduct): string {
  return [product.brand, product.name].filter(Boolean).join(" ");
}

function reactionTone(entry: ReactionEvent): string {
  if (entry.status === "resolved") {
    return "green";
  }
  if (entry.severity === "severe") {
    return "red";
  }
  if (entry.severity === "moderate") {
    return "amber";
  }
  return "yellow";
}

function parseSymptoms(value: string): string[] {
  const seen = new Set<string>();
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => {
      const key = item.toLowerCase();
      if (!item || seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
}

export default function ReactionsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [form, setForm] = useState<ReactionFormState>(() => initialFormState());
  const [message, setMessage] = useState<string | null>(null);

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
    staleTime: authFreshMs,
  });
  const reactionsQuery = useQuery({
    queryKey: ["reactions"],
    queryFn: getReactions,
    enabled: meQuery.isSuccess,
  });
  const routinesQuery = useQuery({
    queryKey: ["routines", "active"],
    queryFn: () => getRoutines(true),
    enabled: meQuery.isSuccess,
  });
  const productsQuery = useQuery({
    queryKey: ["catalog-products"],
    queryFn: () => getCatalogProducts(),
    enabled: meQuery.isSuccess,
    staleTime: authFreshMs,
  });
  const createReactionMutation = useMutation({
    mutationFn: createReaction,
    onSuccess: () => {
      setMessage("Reaction logged.");
      setForm(initialFormState());
      setIsFormOpen(false);
      queryClient.invalidateQueries({ queryKey: ["reactions"] });
    },
    onError: (error) => {
      setMessage(error instanceof Error ? error.message : "Could not save reaction.");
    },
  });
  const resolveReactionMutation = useMutation({
    mutationFn: (entry: ReactionEvent) =>
      updateReaction(entry.id, {
        status: "resolved",
        resolved_on: todayInputValue(),
      }),
    onSuccess: () => {
      setMessage("Reaction marked resolved.");
      queryClient.invalidateQueries({ queryKey: ["reactions"] });
    },
    onError: (error) => {
      setMessage(error instanceof Error ? error.message : "Could not update reaction.");
    },
  });

  useEffect(() => {
    if (meQuery.isError) {
      router.replace("/login");
    }
  }, [meQuery.isError, router]);

  const routines = useMemo(() => routinesQuery.data ?? [], [routinesQuery.data]);
  const products = useMemo(() => productsQuery.data ?? [], [productsQuery.data]);
  const selectedRoutine = routines.find((routine) => String(routine.id) === form.routine_id);
  const routineItems = selectedRoutine?.items ?? [];
  const selectedRoutineItem = routineItems.find(
    (item) => String(item.id) === form.routine_item_id,
  );
  const selectedProduct = products.find(
    (product) => String(product.product_id) === form.product_id,
  );

  if (meQuery.isLoading || meQuery.isError) {
    return <p className="detail-muted">Loading your session...</p>;
  }

  const reactionEntries = reactionsQuery.data ?? [];
  const activeCount = reactionEntries.filter((entry) => entry.status === "active").length;
  const resolvedCount = reactionEntries.filter((entry) => entry.status === "resolved").length;

  function updateForm<K extends keyof ReactionFormState>(
    field: K,
    value: ReactionFormState[K],
  ) {
    setForm((current) => ({ ...current, [field]: value }));
    setMessage(null);
  }

  function selectProduct(value: string) {
    const product = products.find((item) => String(item.product_id) === value);
    setForm((current) => ({
      ...current,
      product_id: value,
      formulation_id: product?.formulation_id ? String(product.formulation_id) : "",
      suspected_trigger:
        current.suspected_trigger || (product ? productLabel(product) : ""),
    }));
    setMessage(null);
  }

  function selectRoutine(value: string) {
    setForm((current) => ({
      ...current,
      routine_id: value,
      routine_item_id: "",
    }));
    setMessage(null);
  }

  function selectRoutineItem(value: string) {
    const item = routineItems.find((routineItem) => String(routineItem.id) === value);
    setForm((current) => ({
      ...current,
      routine_item_id: value,
      product_id: item?.product_id ? String(item.product_id) : current.product_id,
      formulation_id: item?.formulation_id
        ? String(item.formulation_id)
        : current.formulation_id,
      suspected_trigger:
        current.suspected_trigger || (item ? displayRoutineItem(item) : ""),
    }));
    setMessage(null);
  }

  function submitReaction(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const title = form.title.trim();
    if (!title) {
      setMessage("Add a reaction title first.");
      return;
    }
    createReactionMutation.mutate({
      title,
      severity: form.severity,
      status: form.status,
      occurred_on: form.occurred_on || todayInputValue(),
      resolved_on: form.status === "resolved" ? form.resolved_on || todayInputValue() : null,
      symptoms: parseSymptoms(form.symptoms),
      suspected_trigger: form.suspected_trigger.trim(),
      notes: form.notes.trim(),
      routine: form.routine_id ? Number(form.routine_id) : null,
      routine_item: form.routine_item_id ? Number(form.routine_item_id) : null,
      product_id: selectedRoutineItem?.product_id ?? selectedProduct?.product_id ?? null,
      formulation_id:
        selectedRoutineItem?.formulation_id ?? selectedProduct?.formulation_id ?? null,
    });
  }

  return (
    <>
      <div className={styles.reactionsLayout}>
        <AppPageHeader
          title="Reaction Log"
          description="Track adverse reactions and sensitivities."
          action={
            <Button
              className={styles.logButton}
              type="button"
              onPress={() => {
                setIsFormOpen((current) => !current);
                setMessage(null);
              }}
            >
              <span aria-hidden="true">+</span>
              Log
            </Button>
          }
        />

        <section className={styles.statsCard} aria-label="Reaction summary">
          <div>
            <strong>{reactionEntries.length}</strong>
            <span>Total logged</span>
          </div>
          <div>
            <strong>{activeCount}</strong>
            <span>Active</span>
          </div>
          <div>
            <strong>{resolvedCount}</strong>
            <span>Resolved</span>
          </div>
        </section>

        {message ? <p className={styles.statusMessage}>{message}</p> : null}

        {isFormOpen ? (
          <form className={styles.reactionForm} onSubmit={submitReaction}>
            <label className={styles.formField}>
              <span>Reaction</span>
              <input
                required
                value={form.title}
                onChange={(event) => updateForm("title", event.target.value)}
                placeholder="Mild peeling, burning, new breakout..."
              />
            </label>

            <div className={styles.formGrid}>
              <label className={styles.formField}>
                <span>Severity</span>
                <select
                  value={form.severity}
                  onChange={(event) =>
                    updateForm("severity", event.target.value as ReactionEvent["severity"])
                  }
                >
                  <option value="mild">Mild</option>
                  <option value="moderate">Moderate</option>
                  <option value="severe">Severe</option>
                </select>
              </label>
              <label className={styles.formField}>
                <span>Status</span>
                <select
                  value={form.status}
                  onChange={(event) =>
                    updateForm("status", event.target.value as ReactionEvent["status"])
                  }
                >
                  <option value="active">Active</option>
                  <option value="resolved">Resolved</option>
                </select>
              </label>
            </div>

            <div className={styles.formGrid}>
              <label className={styles.formField}>
                <span>Product</span>
                <select
                  value={form.product_id}
                  onChange={(event) => selectProduct(event.target.value)}
                  disabled={productsQuery.isLoading}
                >
                  <option value="">No product selected</option>
                  {products.map((product) => (
                    <option value={product.product_id} key={product.id}>
                      {productLabel(product)}
                    </option>
                  ))}
                </select>
              </label>
              <label className={styles.formField}>
                <span>Routine</span>
                <select
                  value={form.routine_id}
                  onChange={(event) => selectRoutine(event.target.value)}
                  disabled={routinesQuery.isLoading}
                >
                  <option value="">No routine selected</option>
                  {routines.map((routine) => (
                    <option value={routine.id} key={routine.id}>
                      {displayRoutineName(routine)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {form.routine_id ? (
              <label className={styles.formField}>
                <span>Routine item</span>
                <select
                  value={form.routine_item_id}
                  onChange={(event) => selectRoutineItem(event.target.value)}
                  disabled={routineItems.length === 0}
                >
                  <option value="">
                    {routineItems.length > 0
                      ? "No routine item selected"
                      : "No products in routine"}
                  </option>
                  {routineItems.map((item) => (
                    <option value={item.id} key={item.id}>
                      {displayRoutineItem(item)}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            <div className={styles.formGrid}>
              <label className={styles.formField}>
                <span>Occurred</span>
                <input
                  type="date"
                  value={form.occurred_on}
                  onChange={(event) => updateForm("occurred_on", event.target.value)}
                />
              </label>
              {form.status === "resolved" ? (
                <label className={styles.formField}>
                  <span>Resolved</span>
                  <input
                    type="date"
                    value={form.resolved_on}
                    onChange={(event) => updateForm("resolved_on", event.target.value)}
                  />
                </label>
              ) : null}
            </div>

            <label className={styles.formField}>
              <span>Suspected trigger</span>
              <input
                value={form.suspected_trigger}
                onChange={(event) => updateForm("suspected_trigger", event.target.value)}
                placeholder="Product, ingredient, routine step, weather..."
              />
            </label>

            <label className={styles.formField}>
              <span>Symptoms</span>
              <input
                value={form.symptoms}
                onChange={(event) => updateForm("symptoms", event.target.value)}
                placeholder="Comma separated: redness, peeling, stinging"
              />
            </label>

            <label className={styles.formField}>
              <span>Notes</span>
              <textarea
                value={form.notes}
                onChange={(event) => updateForm("notes", event.target.value)}
                placeholder="What changed, how long it lasted, what helped..."
                rows={3}
              />
            </label>

            <div className={styles.formActions}>
              <Button
                className={styles.formSubmit}
                type="submit"
                isDisabled={createReactionMutation.isPending || !form.title.trim()}
              >
                {createReactionMutation.isPending ? "Saving..." : "Save reaction"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onPress={() => {
                  setIsFormOpen(false);
                  setMessage(null);
                }}
              >
                Cancel
              </Button>
            </div>
          </form>
        ) : null}

        <section className={styles.reactionList} aria-label="Logged reactions">
          {reactionsQuery.isLoading ? (
            <p className="detail-muted">Loading reactions...</p>
          ) : reactionsQuery.isError ? (
            <p className="detail-muted">Could not load reactions.</p>
          ) : reactionEntries.length === 0 ? (
            <p className={styles.emptyState}>
              No reactions logged yet. Use Log when a product or routine causes a reaction
              you want to track.
            </p>
          ) : (
            reactionEntries.map((entry) => (
              <article className={styles.reactionCard} key={entry.id}>
                <span
                  className={[
                    styles.reactionDot,
                    styles[`reactionDot${reactionTone(entry)}`],
                  ].join(" ")}
                  aria-hidden="true"
                />
                <div className={styles.reactionInfo}>
                  <div className={styles.reactionTitleRow}>
                    <h2>{entry.title}</h2>
                    {entry.status === "resolved" && (
                      <span className={styles.resolvedIcon} aria-label="Resolved" />
                    )}
                  </div>
                  <p>
                    {reactionContext(entry)} · {formatDate(entry.occurred_on)}
                  </p>
                </div>
                <span className={styles.severityBadge}>{entry.severity}</span>
                {entry.status === "active" ? (
                  <button
                    className={styles.resolveButton}
                    type="button"
                    disabled={resolveReactionMutation.isPending}
                    onClick={() => resolveReactionMutation.mutate(entry)}
                  >
                    Resolve
                  </button>
                ) : (
                  <span className={styles.chevron} aria-hidden="true" />
                )}
              </article>
            ))
          )}
        </section>
      </div>
    </>
  );
}

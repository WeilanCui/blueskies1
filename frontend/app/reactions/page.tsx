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
import {
  goodQuestion,
  inferProductModule,
  noticeabilityQuestion,
  offQuestion,
  orderOptions,
  overallQuestion,
  productModules,
  productTypeOptions,
  questionnaireVersion,
  safetyQuestion,
  timingQuestion,
  useAgainQuestion,
  type ProductModuleKey,
  type QuestionnaireQuestion,
} from "./questionnaire";
import styles from "./reactions.module.css";

const authFreshMs = 5 * 60 * 1000;

type ModuleAnswerMap = Record<string, string[]>;

type ReactionFormState = {
  product_id: string;
  formulation_id: string;
  routine_id: string;
  routine_item_id: string;
  product_type: ProductModuleKey;
  overall: string;
  product_answers: ModuleAnswerMap;
  good: string[];
  off: string[];
  timing: string;
  noticeability: string;
  use_again: string;
  safety: string[];
  occurred_on: string;
  notes: string;
};

type ChipQuestionProps = {
  question: QuestionnaireQuestion;
  values: string[];
  onChange: (values: string[]) => void;
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
    product_id: "",
    formulation_id: "",
    routine_id: "",
    routine_item_id: "",
    product_type: "other",
    overall: "",
    product_answers: {},
    good: [],
    off: [],
    timing: "",
    noticeability: "",
    use_again: "",
    safety: [],
    occurred_on: todayInputValue(),
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
    "Product"
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

function optionLabel(question: QuestionnaireQuestion, value: string): string {
  return question.options.find((option) => option.id === value)?.label ?? "";
}

function optionLabels(question: QuestionnaireQuestion, values: string[]): string[] {
  return values.map((value) => optionLabel(question, value)).filter(Boolean);
}

function productTypeLabel(value: ProductModuleKey): string {
  return productTypeOptions.find((option) => option.id === value)?.label ?? "Other";
}

function uniqueValues(values: string[]): string[] {
  const seen = new Set<string>();
  return values.filter((value) => {
    const key = value.toLowerCase();
    if (!value || seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function joinOrNone(values: string[]): string {
  return values.length > 0 ? values.join(", ") : "None";
}

function readLoggedValue(notes: string, label: string): string {
  const prefix = `${label}:`;
  return (
    notes
      .split("\n")
      .find((line) => line.toLowerCase().startsWith(prefix.toLowerCase()))
      ?.slice(prefix.length)
      .trim() ?? ""
  );
}

function responseLabel(entry: ReactionEvent): string {
  const overall = readLoggedValue(entry.notes, "Overall");
  if (overall) {
    return overall;
  }
  if (entry.severity === "severe") {
    return "Severe";
  }
  if (entry.status === "resolved") {
    return "Closed";
  }
  return entry.severity;
}

function reactionTone(entry: ReactionEvent): string {
  const overall = readLoggedValue(entry.notes, "Overall").toLowerCase();
  if (overall === "loved" || overall === "worked") {
    return "green";
  }
  if (overall === "reaction" || entry.severity === "severe") {
    return "red";
  }
  if (overall === "mismatch" || entry.severity === "moderate") {
    return "amber";
  }
  return "yellow";
}

function isPositiveEntry(entry: ReactionEvent): boolean {
  const overall = readLoggedValue(entry.notes, "Overall").toLowerCase();
  return overall === "loved" || overall === "worked";
}

function hasTriggeredOption(question: QuestionnaireQuestion, values: string[]): boolean {
  return question.options.some(
    (option) => option.triggersSafetyGate && values.includes(option.id),
  );
}

function hasSafetyTrigger(form: ReactionFormState): boolean {
  const moduleQuestions = productModules[form.product_type];
  return (
    hasTriggeredOption(overallQuestion, [form.overall]) ||
    hasTriggeredOption(noticeabilityQuestion, [form.noticeability]) ||
    hasTriggeredOption(useAgainQuestion, [form.use_again]) ||
    hasTriggeredOption(offQuestion, form.off) ||
    moduleQuestions.some((question) =>
      hasTriggeredOption(question, form.product_answers[question.id] ?? []),
    )
  );
}

function computeSeverity(form: ReactionFormState): ReactionEvent["severity"] {
  if (form.safety.length > 0 || form.noticeability === "severe") {
    return "severe";
  }
  if (
    form.noticeability === "moderate" ||
    form.noticeability === "strong" ||
    form.overall === "reaction" ||
    form.overall === "mismatch" ||
    form.off.length > 0
  ) {
    return "moderate";
  }
  return "mild";
}

function computeStatus(form: ReactionFormState): ReactionEvent["status"] {
  if (form.safety.length > 0 || form.overall === "reaction" || hasSafetyTrigger(form)) {
    return "active";
  }
  return "resolved";
}

function ChipQuestion({ question, values, onChange }: ChipQuestionProps) {
  const isSingle = question.type === "single";

  return (
    <fieldset className={styles.chipQuestion}>
      <legend>{question.prompt}</legend>
      <div className={styles.chipGrid}>
        {orderOptions(question.options).map((option) => {
          const isSelected = values.includes(option.id);
          return (
            <label
              className={[styles.answerChip, isSelected ? styles.answerChipSelected : ""]
                .filter(Boolean)
                .join(" ")}
              key={option.id}
            >
              <input
                checked={isSelected}
                name={question.id}
                type={isSingle ? "radio" : "checkbox"}
                value={option.id}
                onChange={() => {
                  if (isSingle) {
                    onChange([option.id]);
                    return;
                  }
                  onChange(
                    isSelected
                      ? values.filter((value) => value !== option.id)
                      : [...values, option.id],
                  );
                }}
              />
              {option.label}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
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
      setMessage("Response saved.");
      setForm(initialFormState());
      setIsFormOpen(false);
      queryClient.invalidateQueries({ queryKey: ["reactions"] });
    },
    onError: (error) => {
      setMessage(error instanceof Error ? error.message : "Could not save response.");
    },
  });
  const resolveReactionMutation = useMutation({
    mutationFn: (entry: ReactionEvent) =>
      updateReaction(entry.id, {
        status: "resolved",
        resolved_on: todayInputValue(),
      }),
    onSuccess: () => {
      setMessage("Marked closed.");
      queryClient.invalidateQueries({ queryKey: ["reactions"] });
    },
    onError: (error) => {
      setMessage(error instanceof Error ? error.message : "Could not update response.");
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
  const moduleQuestions = productModules[form.product_type];
  const showSafetyGate = hasSafetyTrigger(form);

  if (meQuery.isLoading || meQuery.isError) {
    return <p className="detail-muted">Loading your session...</p>;
  }

  const reactionEntries = reactionsQuery.data ?? [];
  const reviewCount = reactionEntries.filter((entry) => entry.status === "active").length;
  const positiveCount = reactionEntries.filter(isPositiveEntry).length;

  function updateForm<K extends keyof ReactionFormState>(
    field: K,
    value: ReactionFormState[K],
  ) {
    setForm((current) => ({ ...current, [field]: value }));
    setMessage(null);
  }

  function updateModuleAnswer(questionId: string, values: string[]) {
    setForm((current) => ({
      ...current,
      product_answers: {
        ...current.product_answers,
        [questionId]: values,
      },
    }));
    setMessage(null);
  }

  function selectProduct(value: string) {
    const product = products.find((item) => String(item.product_id) === value);
    setForm((current) => ({
      ...current,
      product_id: value,
      formulation_id: product?.formulation_id ? String(product.formulation_id) : "",
      product_type: product
        ? inferProductModule(product.category, product.display_name || product.name)
        : current.product_type,
      product_answers: product ? {} : current.product_answers,
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
    const inferredType = item
      ? inferProductModule(item.product?.category, displayRoutineItem(item))
      : form.product_type;
    setForm((current) => ({
      ...current,
      routine_item_id: value,
      product_id: item?.product_id ? String(item.product_id) : current.product_id,
      formulation_id: item?.formulation_id
        ? String(item.formulation_id)
        : current.formulation_id,
      product_type: item ? inferredType : current.product_type,
      product_answers: item ? {} : current.product_answers,
    }));
    setMessage(null);
  }

  function buildSelectedLabels(): string[] {
    const moduleLabels = moduleQuestions.flatMap((question) =>
      optionLabels(question, form.product_answers[question.id] ?? []),
    );
    return uniqueValues([
      ...optionLabels(goodQuestion, form.good),
      ...optionLabels(offQuestion, form.off),
      ...moduleLabels,
      ...optionLabels(safetyQuestion, form.safety),
    ]);
  }

  function buildNotes(): string {
    const lines = [
      `Questionnaire: ${questionnaireVersion}`,
      `Overall: ${optionLabel(overallQuestion, form.overall) || "None"}`,
      `Product type: ${productTypeLabel(form.product_type)}`,
      ...moduleQuestions.map((question) => {
        const labels = optionLabels(question, form.product_answers[question.id] ?? []);
        return `${question.prompt}: ${joinOrNone(labels)}`;
      }),
      `Improved: ${joinOrNone(optionLabels(goodQuestion, form.good))}`,
      `Off: ${joinOrNone(optionLabels(offQuestion, form.off))}`,
      `Timing: ${optionLabel(timingQuestion, form.timing) || "None"}`,
      `Noticeable: ${optionLabel(noticeabilityQuestion, form.noticeability) || "None"}`,
      `Use again: ${optionLabel(useAgainQuestion, form.use_again) || "None"}`,
    ];
    if (showSafetyGate || form.safety.length > 0) {
      lines.push(`Care flags: ${joinOrNone(optionLabels(safetyQuestion, form.safety))}`);
    }
    if (form.notes.trim()) {
      lines.push(`Notes: ${form.notes.trim()}`);
    }
    return lines.join("\n");
  }

  function buildTitle(): string {
    const overall = optionLabel(overallQuestion, form.overall) || "Feedback";
    const context =
      (selectedRoutineItem ? displayRoutineItem(selectedRoutineItem) : "") ||
      (selectedProduct ? productLabel(selectedProduct) : "") ||
      productTypeLabel(form.product_type);
    return `${overall}: ${context}`;
  }

  function submitReaction(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.overall) {
      setMessage("Choose how your skin got along with it.");
      return;
    }

    const severity = computeSeverity(form);
    const status = computeStatus(form);
    createReactionMutation.mutate({
      title: buildTitle(),
      severity,
      status,
      occurred_on: form.occurred_on || todayInputValue(),
      resolved_on: status === "resolved" ? form.occurred_on || todayInputValue() : null,
      symptoms: buildSelectedLabels(),
      suspected_trigger:
        (selectedRoutineItem ? displayRoutineItem(selectedRoutineItem) : "") ||
        (selectedProduct ? productLabel(selectedProduct) : "") ||
        productTypeLabel(form.product_type),
      notes: buildNotes(),
      routine: form.routine_id ? Number(form.routine_id) : null,
      routine_item: form.routine_item_id ? Number(form.routine_item_id) : null,
      product_id:
        selectedRoutineItem?.product_id ??
        selectedProduct?.product_id ??
        (form.product_id ? Number(form.product_id) : null),
      formulation_id:
        selectedRoutineItem?.formulation_id ??
        selectedProduct?.formulation_id ??
        (form.formulation_id ? Number(form.formulation_id) : null),
    });
  }

  return (
    <>
      <div className={styles.reactionsLayout}>
        <AppPageHeader
          title="Product Response Log"
          description="Track how products worked, felt, and fit your routine."
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

        <section className={styles.statsCard} aria-label="Response summary">
          <div>
            <strong>{reactionEntries.length}</strong>
            <span>Total logged</span>
          </div>
          <div>
            <strong>{positiveCount}</strong>
            <span>Liked</span>
          </div>
          <div>
            <strong>{reviewCount}</strong>
            <span>Watch</span>
          </div>
        </section>

        {message ? <p className={styles.statusMessage}>{message}</p> : null}

        {isFormOpen ? (
          <form className={styles.reactionForm} onSubmit={submitReaction}>
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
                <span>Type</span>
                <select
                  value={form.product_type}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      product_type: event.target.value as ProductModuleKey,
                      product_answers: {},
                    }))
                  }
                >
                  {productTypeOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className={styles.formGrid}>
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
              <label className={styles.formField}>
                <span>Routine item</span>
                <select
                  value={form.routine_item_id}
                  onChange={(event) => selectRoutineItem(event.target.value)}
                  disabled={!form.routine_id || routineItems.length === 0}
                >
                  <option value="">
                    {routineItems.length > 0 ? "No item selected" : "No products"}
                  </option>
                  {routineItems.map((item) => (
                    <option value={item.id} key={item.id}>
                      {displayRoutineItem(item)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <ChipQuestion
              question={overallQuestion}
              values={form.overall ? [form.overall] : []}
              onChange={(values) => updateForm("overall", values[0] ?? "")}
            />

            {moduleQuestions.map((question) => (
              <ChipQuestion
                key={question.id}
                question={question}
                values={form.product_answers[question.id] ?? []}
                onChange={(values) => updateModuleAnswer(question.id, values)}
              />
            ))}

            <div className={styles.formGrid}>
              <ChipQuestion
                question={goodQuestion}
                values={form.good}
                onChange={(values) => updateForm("good", values)}
              />
              <ChipQuestion
                question={offQuestion}
                values={form.off}
                onChange={(values) => updateForm("off", values)}
              />
            </div>

            <div className={styles.formGrid}>
              <ChipQuestion
                question={noticeabilityQuestion}
                values={form.noticeability ? [form.noticeability] : []}
                onChange={(values) => updateForm("noticeability", values[0] ?? "")}
              />
              <ChipQuestion
                question={timingQuestion}
                values={form.timing ? [form.timing] : []}
                onChange={(values) => updateForm("timing", values[0] ?? "")}
              />
            </div>

            <ChipQuestion
              question={useAgainQuestion}
              values={form.use_again ? [form.use_again] : []}
              onChange={(values) => updateForm("use_again", values[0] ?? "")}
            />

            {showSafetyGate ? (
              <div className={styles.safetyPanel}>
                <p>
                  This may be bigger than product feedback. Stop using it and contact
                  a healthcare professional if symptoms are severe, spreading, painful,
                  or near your eyes or lips.
                </p>
                <ChipQuestion
                  question={safetyQuestion}
                  values={form.safety}
                  onChange={(values) => updateForm("safety", values)}
                />
                {form.safety.length > 0 ? (
                  <p className={styles.careMessage}>
                    Seek urgent help for breathing trouble, throat swelling, or rapidly
                    worsening symptoms.
                  </p>
                ) : null}
              </div>
            ) : null}

            <div className={styles.formGrid}>
              <label className={styles.formField}>
                <span>Date</span>
                <input
                  type="date"
                  value={form.occurred_on}
                  onChange={(event) => updateForm("occurred_on", event.target.value)}
                />
              </label>
              <label className={styles.formField}>
                <span>Notes</span>
                <textarea
                  value={form.notes}
                  onChange={(event) => updateForm("notes", event.target.value)}
                  placeholder="Anything else?"
                  rows={3}
                />
              </label>
            </div>

            <div className={styles.formActions}>
              <Button
                className={styles.formSubmit}
                type="submit"
                isDisabled={createReactionMutation.isPending || !form.overall}
              >
                {createReactionMutation.isPending ? "Saving..." : "Save response"}
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

        <section className={styles.reactionList} aria-label="Logged responses">
          {reactionsQuery.isLoading ? (
            <p className="detail-muted">Loading responses...</p>
          ) : reactionsQuery.isError ? (
            <p className="detail-muted">Could not load responses.</p>
          ) : reactionEntries.length === 0 ? (
            <p className={styles.emptyState}>
              No product responses logged yet. Use Log after trying a product.
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
                  </div>
                  <p>
                    {reactionContext(entry)} / {formatDate(entry.occurred_on)}
                  </p>
                </div>
                <span className={styles.severityBadge}>{responseLabel(entry)}</span>
                {entry.status === "active" ? (
                  <button
                    className={styles.resolveButton}
                    type="button"
                    disabled={resolveReactionMutation.isPending}
                    onClick={() => resolveReactionMutation.mutate(entry)}
                  >
                    Close
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

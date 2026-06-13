"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AppPageHeader } from "../../components/AppPageHeader";
import { Button } from "../../components/Button";
import {
  createRoutine,
  getCatalogProducts,
  getDailyCheckIns,
  getMe,
  getRoutines,
  getTodayCheckIn,
  saveTodayCheckIn,
  updateRoutine,
  type CatalogProduct,
  type Routine,
  type RoutineItem,
  type RoutineItemPayload,
  type RoutinePayload,
  type RoutineTimeOfDay,
} from "../../lib/appApi";
import styles from "./routine.module.css";

const authFreshMs = 5 * 60 * 1000;

const moods = [
  { id: "radiant", icon: "✦", label: "Radiant" },
  { id: "good", icon: "😊", label: "Good" },
  { id: "okay", icon: "😐", label: "Okay" },
  { id: "rough", icon: "😟", label: "Rough" },
  { id: "bad", icon: "😣", label: "Bad" },
];

const routineSteps = [
  ["cleanser", "Cleanser"],
  ["toner_essence", "Toner / essence"],
  ["treatment", "Treatment"],
  ["moisturizer", "Moisturizer"],
  ["spf", "SPF"],
  ["mask", "Mask"],
  ["exfoliant", "Exfoliant"],
  ["eye_care", "Eye care"],
  ["other", "Other"],
];

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

function routineIcon(timeOfDay: RoutineTimeOfDay): string {
  if (timeOfDay === "am") {
    return "☼";
  }
  if (timeOfDay === "pm") {
    return "☾";
  }
  return "•";
}

function itemToPayload(item: RoutineItem): RoutineItemPayload {
  return {
    id: item.id,
    position: item.position,
    routine_step: item.routine_step,
    custom_step_label: item.custom_step_label,
    product_id: item.product_id ?? item.product?.id ?? null,
    formulation_id: item.formulation_id ?? item.formulation?.id ?? null,
    raw_product_name: item.raw_product_name,
    usage_notes: item.usage_notes,
    frequency: item.frequency,
    schedule: item.schedule,
  };
}

function routineToPayload(routine: Routine, items: RoutineItemPayload[]): RoutinePayload {
  return {
    name: routine.name,
    time_of_day: routine.time_of_day,
    custom_time_label: routine.custom_time_label,
    is_active: routine.is_active,
    notes: routine.notes,
    items,
  };
}

function productToRoutineItem(product: CatalogProduct, position: number): RoutineItemPayload {
  return {
    position,
    routine_step: product.category.toLowerCase().includes("cleanser")
      ? "cleanser"
      : product.category.toLowerCase().includes("spf")
        ? "spf"
        : product.category.toLowerCase().includes("moistur")
          ? "moisturizer"
          : "treatment",
    product_id: product.product_id,
    formulation_id: product.formulation_id,
    raw_product_name: "",
  };
}

function reorderRoutineItems(items: RoutineItem[], fromId: number, toId: number): RoutineItem[] {
  const fromIndex = items.findIndex((item) => item.id === fromId);
  const toIndex = items.findIndex((item) => item.id === toId);
  if (fromIndex === -1 || toIndex === -1 || fromIndex === toIndex) {
    return items;
  }

  const next = [...items];
  const [moved] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, moved);
  return next;
}

type DragState = {
  routineId: number;
  itemId: number;
};

export default function RoutinePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeView, setActiveView] = useState<"log" | "history" | "routine">("log");
  const [selectedRoutineId, setSelectedRoutineId] = useState<number | null>(null);
  const [completed, setCompleted] = useState<number[]>([]);
  const [skinFeel, setSkinFeel] = useState("good");
  const [notes, setNotes] = useState("");
  const [addTimeOfDay, setAddTimeOfDay] = useState<RoutineTimeOfDay>("am");
  const [customLabel, setCustomLabel] = useState("");
  const [selectedProductId, setSelectedProductId] = useState("");
  const [manualProductName, setManualProductName] = useState("");
  const [selectedStep, setSelectedStep] = useState("treatment");
  const [message, setMessage] = useState<string | null>(null);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [dragOverItemId, setDragOverItemId] = useState<number | null>(null);

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
    staleTime: authFreshMs,
  });
  const routinesQuery = useQuery({
    queryKey: ["routines", "active"],
    queryFn: () => getRoutines(true),
    enabled: meQuery.isSuccess,
  });
  const todayQuery = useQuery({
    queryKey: ["daily-checkins", "today"],
    queryFn: getTodayCheckIn,
    enabled: meQuery.isSuccess,
  });
  const historyQuery = useQuery({
    queryKey: ["daily-checkins"],
    queryFn: getDailyCheckIns,
    enabled: meQuery.isSuccess,
  });
  const productsQuery = useQuery({
    queryKey: ["catalog-products"],
    queryFn: () => getCatalogProducts(),
    enabled: meQuery.isSuccess,
    staleTime: authFreshMs,
  });
  const saveLogMutation = useMutation({
    mutationFn: saveTodayCheckIn,
    onSuccess: (data) => {
      setMessage("Today's routine log is saved.");
      setCompleted(data.completed_routine_item_ids);
      queryClient.setQueryData(["daily-checkins", "today"], data);
      queryClient.invalidateQueries({ queryKey: ["daily-checkins"] });
    },
  });
  const saveRoutineMutation = useMutation({
    mutationFn: async (payload: { routine?: Routine; item: RoutineItemPayload }) => {
      if (payload.routine) {
        const items = [
          ...payload.routine.items.map(itemToPayload),
          payload.item,
        ].map((item, index) => ({ ...item, position: index + 1 }));
        return updateRoutine(payload.routine.id, routineToPayload(payload.routine, items));
      }
      const label = payload.item.raw_product_name || "Routine";
      return createRoutine({
        name:
          addTimeOfDay === "custom"
            ? customLabel.trim() || label
            : addTimeOfDay === "am"
              ? "AM Routine"
              : "PM Routine",
        time_of_day: addTimeOfDay,
        custom_time_label: addTimeOfDay === "custom" ? customLabel.trim() : "",
        is_active: true,
        items: [payload.item],
      });
    },
    onSuccess: () => {
      setMessage("Routine updated.");
      setManualProductName("");
      setSelectedProductId("");
      queryClient.invalidateQueries({ queryKey: ["routines"] });
    },
  });
  const reorderRoutineMutation = useMutation({
    mutationFn: async (payload: { routine: Routine; items: RoutineItem[] }) => {
      const items = payload.items.map((item, index) => ({
        ...itemToPayload(item),
        position: index + 1,
      }));
      return updateRoutine(payload.routine.id, routineToPayload(payload.routine, items));
    },
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: ["routines", "active"] });
      const previous = queryClient.getQueryData<Routine[]>(["routines", "active"]);
      queryClient.setQueryData<Routine[]>(["routines", "active"], (current) =>
        current?.map((routine) =>
          routine.id === payload.routine.id
            ? {
              ...routine,
              items: payload.items.map((item, index) => ({
                ...item,
                position: index + 1,
              })),
            }
            : routine,
        ),
      );
      return { previous };
    },
    onSuccess: () => {
      setMessage("Routine order saved.");
      queryClient.invalidateQueries({ queryKey: ["routines"] });
    },
    onError: (_error, _payload, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["routines", "active"], context.previous);
      }
      setMessage("Could not save routine order.");
    },
  });

  useEffect(() => {
    if (meQuery.isError) {
      router.replace("/login");
    }
  }, [meQuery.isError, router]);

  useEffect(() => {
    const today = todayQuery.data;
    if (!today) {
      return;
    }
    setCompleted(today.completed_routine_item_ids);
    setSkinFeel(today.skin_feel || "good");
    setNotes(today.skin_notes || "");
  }, [todayQuery.data]);

  const routines = routinesQuery.data ?? [];
  const products = productsQuery.data ?? [];
  const selectedRoutine = useMemo(() => {
    if (selectedRoutineId !== null) {
      return routines.find((routine) => routine.id === selectedRoutineId) ?? null;
    }
    return routines.find((routine) => routine.time_of_day === "am") ?? routines[0] ?? null;
  }, [routines, selectedRoutineId]);
  const visibleItems = selectedRoutine?.items ?? [];
  const completionText = `${completed.filter((id) => visibleItems.some((item) => item.id === id)).length}/${visibleItems.length} complete`;

  function toggleComplete(itemId: number) {
    setCompleted((current) =>
      current.includes(itemId)
        ? current.filter((id) => id !== itemId)
        : [...current, itemId],
    );
  }

  function saveLog() {
    saveLogMutation.mutate({
      skin_feel: skinFeel,
      skin_notes: notes,
      completed_routine_item_ids: completed,
    });
  }

  function addRoutineItem() {
    const existingRoutine =
      addTimeOfDay === "custom"
        ? routines.find(
          (routine) =>
            routine.time_of_day === "custom" &&
            routine.custom_time_label.toLowerCase() === customLabel.trim().toLowerCase(),
        )
        : routines.find((routine) => routine.time_of_day === addTimeOfDay);
    const position = (existingRoutine?.items.length ?? 0) + 1;
    const selectedProduct = products.find(
      (product) => String(product.product_id) === selectedProductId,
    );
    const item = selectedProduct
      ? productToRoutineItem(selectedProduct, position)
      : {
        position,
        routine_step: selectedStep,
        raw_product_name: manualProductName.trim(),
      };
    if (!selectedProduct && !manualProductName.trim()) {
      setMessage("Choose a catalog product or enter a product name.");
      return;
    }
    if (addTimeOfDay === "custom" && !customLabel.trim()) {
      setMessage("Add a custom routine label first.");
      return;
    }
    saveRoutineMutation.mutate({ routine: existingRoutine, item });
  }

  function handleRoutineReorder(routine: Routine, fromId: number, toId: number) {
    const reordered = reorderRoutineItems(routine.items, fromId, toId);
    if (reordered === routine.items) {
      return;
    }
    reorderRoutineMutation.mutate({ routine, items: reordered });
  }

  function clearDragState() {
    setDragState(null);
    setDragOverItemId(null);
  }

  if (meQuery.isLoading || meQuery.isError) {
    return <p className="detail-muted">Loading your session...</p>;
  }

  return (
    <>
      <div className={styles.routineLayout}>
        <AppPageHeader
          title="Routine Tracker"
          description="Log your skincare and track skin health over time."
        />

        <section className={styles.viewTabs} aria-label="Routine views">
          {[
            ["log", "Log Today"],
            ["history", "History"],
            ["routine", "My Routine"],
          ].map(([value, label]) => (
            <button
              className={
                activeView === value
                  ? [styles.viewTab, styles.viewTabActive].join(" ")
                  : styles.viewTab
              }
              key={value}
              type="button"
              onClick={() => setActiveView(value as typeof activeView)}
            >
              {label}
            </button>
          ))}
        </section>

        {message ? <p className={styles.statusMessage}>{message}</p> : null}

        {activeView === "log" && (
          <>
            <section className={styles.dayToggle} aria-label="Routine time">
              {routines.length > 0 ? (
                routines.map((routine) => (
                  <button
                    className={
                      selectedRoutine?.id === routine.id
                        ? [styles.dayButton, styles.dayButtonActive].join(" ")
                        : styles.dayButton
                    }
                    key={routine.id}
                    type="button"
                    onClick={() => setSelectedRoutineId(routine.id)}
                  >
                    <span aria-hidden="true">{routineIcon(routine.time_of_day)}</span>
                    {displayRoutineName(routine)}
                  </button>
                ))
              ) : (
                <p className={styles.emptyState}>
                  Build your first routine in My Routine, then come back to log it.
                </p>
              )}
            </section>

            {selectedRoutine ? (
              <section
                className={styles.checklist}
                aria-label={`${displayRoutineName(selectedRoutine)} checklist`}
              >
                {visibleItems.map((item) => {
                  const isComplete = completed.includes(item.id);
                  return (
                    <button
                      className={
                        isComplete
                          ? [styles.routineItem, styles.routineItemComplete].join(" ")
                          : styles.routineItem
                      }
                      key={item.id}
                      type="button"
                      onClick={() => toggleComplete(item.id)}
                    >
                      <span className={styles.checkCircle} aria-hidden="true" />
                      <span>
                        <strong>{item.display_name}</strong>
                        <em>{item.product?.brand || item.routine_step}</em>
                      </span>
                    </button>
                  );
                })}
              </section>
            ) : null}

            <section className={styles.skinFeelCard}>
              <div className={styles.cardHeading}>
                <h2>How does your skin feel today?</h2>
                <span>{completionText}</span>
              </div>
              <div className={styles.moodGrid}>
                {moods.map((mood) => (
                  <button
                    className={
                      skinFeel === mood.id
                        ? [styles.moodButton, styles.moodButtonActive].join(" ")
                        : styles.moodButton
                    }
                    key={mood.id}
                    type="button"
                    onClick={() => setSkinFeel(mood.id)}
                  >
                    <span aria-hidden="true">{mood.icon}</span>
                    <strong>{mood.label}</strong>
                  </button>
                ))}
              </div>
            </section>

            <label className={styles.notesField}>
              <span className="sr-only">Routine notes</span>
              <textarea
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Any notes? Redness, new breakout, extra glow..."
                rows={4}
              />
            </label>

            <Button
              className={styles.saveButton}
              type="button"
              isDisabled={saveLogMutation.isPending}
              onPress={saveLog}
            >
              {saveLogMutation.isPending ? "Saving..." : "Save today's log"}
            </Button>
          </>
        )}

        {activeView === "history" && (
          <section className={styles.historyPanel}>
            <h2>History</h2>
            {historyQuery.data && historyQuery.data.length > 0 ? (
              historyQuery.data.slice(0, 5).map((checkin) => (
                <div className={styles.historyPreview} key={checkin.id}>
                  <span>{checkin.checkin_date}</span>
                  <strong>{checkin.product_uses.length} products logged</strong>
                  <em>{checkin.skin_feel || "No skin feel"}</em>
                </div>
              ))
            ) : (
              <p>Your routine logs will appear here after you save daily check-ins.</p>
            )}
          </section>
        )}

        {activeView === "routine" && (
          <section className={styles.myRoutineView}>
            <article className={styles.routineGroup}>
              <div className={styles.routineGroupHeader}>
                <div>
                  <span aria-hidden="true">+</span>
                  <h2>Add product</h2>
                </div>
                <strong>Catalog or manual</strong>
              </div>
              <div className={styles.routineAddGrid}>
                <label>
                  <span>Routine</span>
                  <select
                    value={addTimeOfDay}
                    onChange={(event) => setAddTimeOfDay(event.target.value as RoutineTimeOfDay)}
                  >
                    <option value="am">AM Routine</option>
                    <option value="pm">PM Routine</option>
                    <option value="custom">Custom</option>
                  </select>
                </label>
                {addTimeOfDay === "custom" ? (
                  <label>
                    <span>Custom label</span>
                    <input
                      value={customLabel}
                      onChange={(event) => setCustomLabel(event.target.value)}
                      placeholder="Post-workout, weekly mask..."
                    />
                  </label>
                ) : null}
                <label>
                  <span>Catalog product</span>
                  <select
                    value={selectedProductId}
                    onChange={(event) => setSelectedProductId(event.target.value)}
                  >
                    <option value="">Choose product...</option>
                    {products.map((product) => (
                      <option value={product.product_id} key={product.id}>
                        {product.brand} {product.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Manual product</span>
                  <input
                    value={manualProductName}
                    onChange={(event) => setManualProductName(event.target.value)}
                    placeholder="Or type a product name"
                  />
                </label>
                <label>
                  <span>Step</span>
                  <select
                    value={selectedStep}
                    onChange={(event) => setSelectedStep(event.target.value)}
                    disabled={Boolean(selectedProductId)}
                  >
                    {routineSteps.map(([value, label]) => (
                      <option value={value} key={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <Button
                className={styles.saveButton}
                type="button"
                isDisabled={saveRoutineMutation.isPending}
                onPress={addRoutineItem}
              >
                {saveRoutineMutation.isPending ? "Adding..." : "Add to routine"}
              </Button>
            </article>

            {routines.map((routine) => (
              <article className={styles.routineGroup} key={routine.id}>
                <div className={styles.routineGroupHeader}>
                  <div>
                    <span>{routineIcon(routine.time_of_day)}</span>
                    <h2>{displayRoutineName(routine)}</h2>
                  </div>
                  <strong>{routine.items.length} products</strong>
                </div>
                <div className={styles.routineProductList} role="list">
                  {routine.items.length > 0 ? (
                    <>
                      <p className={styles.dragHint}>Drag products to reorder your routine.</p>
                      {routine.items.map((item, index) => {
                        const isDragging =
                          dragState?.routineId === routine.id && dragState.itemId === item.id;
                        const isDragOver =
                          dragOverItemId === item.id &&
                          dragState?.routineId === routine.id &&
                          dragState.itemId !== item.id;

                        return (
                          <div
                            className={[
                              styles.routineProductCard,
                              isDragging ? styles.routineProductCardDragging : "",
                              isDragOver ? styles.routineProductCardDragOver : "",
                            ]
                              .filter(Boolean)
                              .join(" ")}
                            draggable={!reorderRoutineMutation.isPending}
                            key={item.id}
                            role="listitem"
                            aria-grabbed={isDragging}
                            onDragStart={(event) => {
                              event.dataTransfer.effectAllowed = "move";
                              event.dataTransfer.setData("text/plain", String(item.id));
                              setDragState({ routineId: routine.id, itemId: item.id });
                            }}
                            onDragOver={(event) => {
                              if (!dragState || dragState.routineId !== routine.id) {
                                return;
                              }
                              event.preventDefault();
                              event.dataTransfer.dropEffect = "move";
                              setDragOverItemId(item.id);
                            }}
                            onDragLeave={() => {
                              if (dragOverItemId === item.id) {
                                setDragOverItemId(null);
                              }
                            }}
                            onDrop={(event) => {
                              event.preventDefault();
                              if (!dragState || dragState.routineId !== routine.id) {
                                clearDragState();
                                return;
                              }
                              handleRoutineReorder(routine, dragState.itemId, item.id);
                              clearDragState();
                            }}
                            onDragEnd={clearDragState}
                          >
                            <span className={styles.dragHandle} aria-hidden="true">
                              ⋮⋮
                            </span>
                            <span>{index + 1}</span>
                            <div>
                              <strong>{item.display_name}</strong>
                              <em>{item.product?.brand || item.raw_product_name || item.routine_step}</em>
                            </div>
                            <small>{item.routine_step}</small>
                          </div>
                        );
                      })}
                    </>
                  ) : (
                    <p className={styles.emptyState}>No products in this routine yet.</p>
                  )}
                </div>
              </article>
            ))}
          </section>
        )}
      </div>
    </>
  );
}

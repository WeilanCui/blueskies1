"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AppChrome } from "../../components/AppChrome";
import { Button } from "../../components/Button";
import { getMe } from "../../lib/appApi";
import styles from "./routine.module.css";

const authFreshMs = 5 * 60 * 1000;

const routineItems = {
  am: [
    { id: "cleanser", name: "Gentle Foaming Cleanser", brand: "CeraVe", step: "Cleanse" },
    { id: "vitamin-c", name: "Vitamin C Serum 15%", brand: "Paula's Choice", step: "Treat" },
    { id: "cream", name: "Ultra Facial Cream", brand: "Kiehl's", step: "Moisturize" },
    { id: "spf", name: "Daily Moisturizing Sunscreen SPF 50", brand: "EltaMD", step: "Protect" },
  ],
  pm: [
    { id: "cleanser-pm", name: "Gentle Foaming Cleanser", brand: "CeraVe", step: "Cleanse" },
    { id: "retinol", name: "Retinol 0.3% in Squalane", brand: "The Ordinary", step: "Treat" },
    { id: "cream-pm", name: "Ultra Facial Cream", brand: "Kiehl's", step: "Moisturize" },
  ],
};

const moods = [
  { id: "radiant", icon: "✦", label: "Radiant" },
  { id: "good", icon: "😊", label: "Good" },
  { id: "okay", icon: "😐", label: "Okay" },
  { id: "rough", icon: "😟", label: "Rough" },
  { id: "bad", icon: "😣", label: "Bad" },
];

export default function RoutinePage() {
  const router = useRouter();
  const [activeView, setActiveView] = useState<"log" | "history" | "routine">("log");
  const [timeOfDay, setTimeOfDay] = useState<"am" | "pm">("am");
  const [completed, setCompleted] = useState<string[]>([]);
  const [skinFeel, setSkinFeel] = useState("good");
  const [notes, setNotes] = useState("");

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
    staleTime: authFreshMs,
  });
  useEffect(() => {
    if (meQuery.isError) {
      router.replace("/login");
    }
  }, [meQuery.isError, router]);

  const visibleItems = routineItems[timeOfDay];
  const completionText = useMemo(
    () => `${completed.length}/${visibleItems.length} complete`,
    [completed.length, visibleItems.length],
  );

  function toggleComplete(itemId: string) {
    setCompleted((current) =>
      current.includes(itemId)
        ? current.filter((id) => id !== itemId)
        : [...current, itemId],
    );
  }

  if (meQuery.isLoading || meQuery.isError) {
    return (
      <main className={styles.routineShell}>
        <p className="detail-muted">Loading your session...</p>
      </main>
    );
  }

  return (
    <main className={styles.routineShell}>
      <AppChrome active="routine" />

      <div className={styles.routineLayout}>
        <section className={styles.routineHero}>
          <h1>Routine Tracker</h1>
          <p>Log your skincare and track skin health over time.</p>
        </section>

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

        {activeView === "log" && (
          <>
            <section className={styles.dayToggle} aria-label="Routine time">
              <button
                className={
                  timeOfDay === "am"
                    ? [styles.dayButton, styles.dayButtonActive].join(" ")
                    : styles.dayButton
                }
                type="button"
                onClick={() => {
                  setTimeOfDay("am");
                  setCompleted([]);
                }}
              >
                <span aria-hidden="true">☼</span>
                AM Routine
              </button>
              <button
                className={
                  timeOfDay === "pm"
                    ? [styles.dayButton, styles.dayButtonActive].join(" ")
                    : styles.dayButton
                }
                type="button"
                onClick={() => {
                  setTimeOfDay("pm");
                  setCompleted([]);
                }}
              >
                <span aria-hidden="true">☾</span>
                PM Routine
              </button>
            </section>

            <section className={styles.checklist} aria-label={`${timeOfDay.toUpperCase()} routine`}>
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
                      <strong>{item.name}</strong>
                      <em>{item.brand}</em>
                    </span>
                  </button>
                );
              })}
            </section>

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

            <Button className={styles.saveButton} type="button">
              Save today's log
            </Button>
          </>
        )}

        {activeView === "history" && (
          <section className={styles.historyPanel}>
            <h2>History</h2>
            <p>Your routine logs will appear here after you save daily check-ins.</p>
            <div className={styles.historyPreview}>
              <span>Today</span>
              <strong>{completionText}</strong>
              <em>{skinFeel}</em>
            </div>
          </section>
        )}

        {activeView === "routine" && (
          <section className={styles.myRoutineView}>
            {(["am", "pm"] as const).map((routineKey) => (
              <article className={styles.routineGroup} key={routineKey}>
                <div className={styles.routineGroupHeader}>
                  <div>
                    <span>{routineKey === "am" ? "☼" : "☾"}</span>
                    <h2>{routineKey === "am" ? "AM Routine" : "PM Routine"}</h2>
                  </div>
                  <strong>{routineItems[routineKey].length} products</strong>
                </div>
                <div className={styles.routineProductList}>
                  {routineItems[routineKey].map((item, index) => (
                    <div className={styles.routineProductCard} key={item.id}>
                      <span>{index + 1}</span>
                      <div>
                        <strong>{item.name}</strong>
                        <em>{item.brand}</em>
                      </div>
                      <small>{item.step}</small>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </section>
        )}
      </div>

    </main>
  );
}

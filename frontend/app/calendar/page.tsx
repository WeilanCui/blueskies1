"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  type DailyCheckIn,
  getDailyCheckIns,
  getMe,
  getReactions,
  type ReactionEvent,
} from "../../lib/appApi";
import styles from "./calendar.module.css";

const authFreshMs = 5 * 60 * 1000;
const weekDays = [
  { key: "mon", label: "M" },
  { key: "tue", label: "T" },
  { key: "wed", label: "W" },
  { key: "thu", label: "T" },
  { key: "fri", label: "F" },
  { key: "sat", label: "S" },
  { key: "sun", label: "S" },
];
const filterTabs = ["Condition", "By product", "Effort"] as const;

type FilterTab = (typeof filterTabs)[number];

function parseLocalDate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function toDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function conditionScore(checkIn: DailyCheckIn | undefined): number | null {
  if (!checkIn) {
    return null;
  }

  const value = checkIn.skin_feel.toLowerCase();
  if (["great", "good", "calm"].includes(value)) {
    return 5;
  }
  if (["neutral", "okay", "fine"].includes(value)) {
    return 3;
  }
  if (["bad", "rough", "flare"].includes(value)) {
    return 1;
  }
  return checkIn.symptoms.length > 0 ? 2 : 3;
}

function conditionClass(score: number | null): string {
  if (score === null) {
    return styles.dayEmpty;
  }
  if (score >= 5) {
    return styles.dayGreat;
  }
  if (score >= 3) {
    return styles.dayOkay;
  }
  return styles.dayRough;
}

function monthLabel(date: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "long",
    year: "numeric",
  }).format(date);
}

function shortDateLabel(date: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(date);
}

function conditionLabel(score: number | null): string {
  if (score === null) {
    return "No entry";
  }
  if (score >= 5) {
    return "Great";
  }
  if (score >= 3) {
    return "Okay";
  }
  return "Rough";
}

function productName(use: DailyCheckIn["product_uses"][number]): string {
  return (
    use.product?.display_name ||
    use.routine_item?.display_name ||
    use.formulation?.name ||
    use.raw_product_name ||
    "Product"
  );
}

function reactionProductName(reaction: ReactionEvent): string | null {
  return (
    reaction.product?.display_name ||
    reaction.formulation?.name ||
    reaction.suspected_trigger ||
    null
  );
}

function formatStep(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function buildProductRows(checkIns: DailyCheckIn[]) {
  const rows = new Map<string, { total: number; count: number }>();

  for (const checkIn of checkIns) {
    const score = conditionScore(checkIn) ?? 3;
    for (const use of checkIn.product_uses) {
      const name = productName(use);
      const row = rows.get(name) ?? { total: 0, count: 0 };
      row.total += score;
      row.count += 1;
      rows.set(name, row);
    }
  }

  if (rows.size === 0) {
    return [];
  }

  const allScores = checkIns
    .map((checkIn) => conditionScore(checkIn))
    .filter((score): score is number => score !== null);
  const baseline =
    allScores.reduce((sum, score) => sum + score, 0) /
    Math.max(allScores.length, 1);

  return Array.from(rows.entries())
    .map(([name, row]) => ({
      name,
      delta: `${row.total / row.count - baseline >= 0 ? "+" : ""}${(
        row.total / row.count - baseline
      ).toFixed(1)}`,
    }))
    .sort((a, b) => Number(b.delta) - Number(a.delta))
    .slice(0, 4);
}

export default function CalendarPage() {
  const router = useRouter();
  const [activeFilter, setActiveFilter] = useState<FilterTab>("Condition");
  const [hasDefaultedDate, setHasDefaultedDate] = useState(false);
  const [selectedDateKey, setSelectedDateKey] = useState(() =>
    toDateKey(new Date()),
  );

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
    staleTime: authFreshMs,
  });
  const checkInsQuery = useQuery({
    queryKey: ["daily-checkins"],
    queryFn: getDailyCheckIns,
    enabled: meQuery.isSuccess,
    retry: false,
  });
  const reactionsQuery = useQuery({
    queryKey: ["reactions"],
    queryFn: getReactions,
    enabled: meQuery.isSuccess,
    retry: false,
  });

  useEffect(() => {
    if (meQuery.isError) {
      router.replace("/login");
    }
  }, [meQuery.isError, router]);

  const checkIns = checkInsQuery.data ?? [];
  const reactions = reactionsQuery.data ?? [];
  useEffect(() => {
    if (!hasDefaultedDate && checkIns.length > 0) {
      setSelectedDateKey(checkIns[0].checkin_date);
      setHasDefaultedDate(true);
    }
  }, [checkIns, hasDefaultedDate]);

  const selectedDate = parseLocalDate(selectedDateKey);
  const visibleMonthDate = selectedDate;
  const monthStart = new Date(
    visibleMonthDate.getFullYear(),
    visibleMonthDate.getMonth(),
    1,
  );
  const daysInMonth = new Date(
    visibleMonthDate.getFullYear(),
    visibleMonthDate.getMonth() + 1,
    0,
  ).getDate();
  const leadingBlanks = (monthStart.getDay() + 6) % 7;
  const checkInsByDate = useMemo(
    () => new Map(checkIns.map((checkIn) => [checkIn.checkin_date, checkIn])),
    [checkIns],
  );
  const reactionsByDate = useMemo(() => {
    const grouped = new Map<string, ReactionEvent[]>();
    for (const reaction of reactions) {
      const current = grouped.get(reaction.occurred_on) ?? [];
      current.push(reaction);
      grouped.set(reaction.occurred_on, current);
    }
    return grouped;
  }, [reactions]);
  const selectedCheckIn = checkInsByDate.get(toDateKey(selectedDate)) ?? null;
  const selectedReactions = reactions.filter(
    (reaction) =>
      reaction.occurred_on === toDateKey(selectedDate) ||
      (selectedCheckIn !== null &&
        reaction.daily_checkin === selectedCheckIn.id),
  );
  const productRows = useMemo(() => buildProductRows(checkIns), [checkIns]);
  const selectedScore = conditionScore(selectedCheckIn ?? undefined);
  const selectedProducts = selectedCheckIn?.product_uses ?? [];

  if (meQuery.isLoading || meQuery.isError || !meQuery.data) {
    return <p className="detail-muted">Loading your calendar...</p>;
  }

  return (
    <main className={styles.calendarPage}>
      <section className={styles.intro}>
        <div>
          <p className={styles.eyebrow}>Insights</p>
          <h1>Calendar</h1>
        </div>
      </section>

      <section className={styles.segmented} aria-label="Calendar lenses">
        {filterTabs.map((tab) => (
          <button
            className={
              activeFilter === tab
                ? [styles.segmentButton, styles.segmentButtonActive].join(" ")
                : styles.segmentButton
            }
            key={tab}
            onClick={() => setActiveFilter(tab)}
            type="button"
          >
            {tab}
          </button>
        ))}
      </section>

      <section
        className={styles.monthCard}
        aria-label={monthLabel(selectedDate)}
      >
        <div className={styles.monthHeader}>
          <h2>{monthLabel(selectedDate)}</h2>
          <span>{activeFilter}</span>
        </div>
        <div className={styles.weekHeader}>
          {weekDays.map((day) => (
            <span key={day.key}>{day.label}</span>
          ))}
        </div>
        <div className={styles.monthGrid}>
          {Array.from(
            { length: leadingBlanks },
            (_, index) => `spacer-${index + 1}`,
          ).map((key) => (
            <span aria-hidden="true" className={styles.daySpacer} key={key} />
          ))}
          {Array.from({ length: daysInMonth }, (_, index) => index + 1).map(
            (day) => {
              const date = new Date(
                visibleMonthDate.getFullYear(),
                visibleMonthDate.getMonth(),
                day,
              );
              const key = toDateKey(date);
              const checkIn = checkInsByDate.get(key);
              const score = conditionScore(checkIn);
              const hasReaction = (reactionsByDate.get(key) ?? []).length > 0;

              return (
                <button
                  aria-label={`${shortDateLabel(date)}${
                    score ? ` condition ${score} of 5` : " no entry"
                  }`}
                  aria-pressed={key === toDateKey(selectedDate)}
                  className={[
                    styles.dayCell,
                    conditionClass(score),
                    hasReaction ? styles.dayWithReaction : "",
                    key === toDateKey(selectedDate) ? styles.daySelected : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  key={key}
                  onClick={() => setSelectedDateKey(key)}
                  type="button"
                >
                  {day}
                </button>
              );
            },
          )}
        </div>
        <div className={styles.legend}>
          <span>Amber = reaction flagged</span>
          <span className={styles.legendScale}>
            rough
            {[1, 2, 3, 4, 5].map((level) => (
              <i
                className={[styles.legendDot, conditionClass(level)].join(" ")}
                key={level}
              />
            ))}
            great
          </span>
        </div>
      </section>

      <section className={styles.dayCard}>
        <div className={styles.dayCardHeader}>
          <h2>{shortDateLabel(selectedDate)}</h2>
          <span>
            {conditionLabel(selectedScore)}
            {selectedScore === null ? "" : ` · ${selectedScore}/5`}
          </span>
        </div>
        <p>
          {selectedCheckIn?.skin_notes ||
            "No skin notes were logged for this day yet."}
        </p>
        {(selectedCheckIn?.symptoms.length ?? 0) > 0 && (
          <div className={styles.tagList}>
            {selectedCheckIn?.symptoms.map((symptom) => (
              <span key={symptom}>{formatStep(symptom)}</span>
            ))}
          </div>
        )}
      </section>

      <section className={styles.detailCard}>
        <div className={styles.cardHeader}>
          <h2>Routines</h2>
          <p>Products and routine steps logged on this date.</p>
        </div>
        {selectedProducts.length > 0 ? (
          <div className={styles.detailList}>
            {selectedProducts.map((use) => (
              <div className={styles.detailRow} key={use.id}>
                <div>
                  <strong>{productName(use)}</strong>
                  <span>
                    {formatStep(use.time_of_day)}
                    {use.routine_step
                      ? ` · ${formatStep(use.routine_step)}`
                      : ""}
                  </span>
                </div>
                {use.notes && <p>{use.notes}</p>}
              </div>
            ))}
          </div>
        ) : (
          <p className={styles.emptyText}>No routine products logged.</p>
        )}
      </section>

      <section className={styles.detailCard}>
        <div className={styles.cardHeader}>
          <h2>Reactions</h2>
          <p>Reaction events associated with this date.</p>
        </div>
        {selectedReactions.length > 0 ? (
          <div className={styles.detailList}>
            {selectedReactions.map((reaction) => (
              <div className={styles.detailRow} key={reaction.id}>
                <div>
                  <strong>{reaction.title}</strong>
                  <span>
                    {formatStep(reaction.severity)} ·{" "}
                    {formatStep(reaction.status)}
                    {reactionProductName(reaction)
                      ? ` · ${reactionProductName(reaction)}`
                      : ""}
                  </span>
                </div>
                {reaction.symptoms.length > 0 && (
                  <div className={styles.tagList}>
                    {reaction.symptoms.map((symptom) => (
                      <span key={symptom}>{formatStep(symptom)}</span>
                    ))}
                  </div>
                )}
                {reaction.notes && <p>{reaction.notes}</p>}
              </div>
            ))}
          </div>
        ) : (
          <p className={styles.emptyText}>No reactions logged.</p>
        )}
      </section>

      <section className={styles.productCard}>
        <div className={styles.cardHeader}>
          <h2>Per product</h2>
          <p>Average condition on days used, against the rest.</p>
        </div>
        {productRows.length > 0 ? (
          <div className={styles.productList}>
            {productRows.map((row) => (
              <div className={styles.productRow} key={row.name}>
                <span>{row.name}</span>
                <strong>{row.delta}</strong>
              </div>
            ))}
          </div>
        ) : (
          <p className={styles.emptyText}>No product comparisons yet.</p>
        )}
      </section>
    </main>
  );
}

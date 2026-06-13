"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppPageHeader } from "../../components/AppPageHeader";
import { Button } from "../../components/Button";
import { getMe } from "../../lib/appApi";
import styles from "./reactions.module.css";

const authFreshMs = 5 * 60 * 1000;

const reactionEntries = [
  {
    id: "peeling-retinol",
    title: "Mild peeling",
    product: "Retinol 0.3% in Squalane",
    date: "Jun 7",
    severity: "mild",
    status: "active",
    tone: "amber",
  },
  {
    id: "tingling-vitamin-c",
    title: "Slight tingling",
    product: "Vitamin C Serum 15%",
    date: "Jun 2",
    severity: "mild",
    status: "resolved",
    tone: "yellow",
  },
];

export default function ReactionsPage() {
  const router = useRouter();

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

  if (meQuery.isLoading || meQuery.isError) {
    return <p className="detail-muted">Loading your session...</p>;
  }

  const activeCount = reactionEntries.filter((entry) => entry.status === "active").length;
  const resolvedCount = reactionEntries.filter((entry) => entry.status === "resolved").length;

  return (
    <>
      <div className={styles.reactionsLayout}>
        <AppPageHeader
          title="Reaction Log"
          description="Track adverse reactions and sensitivities."
          action={
            <Button className={styles.logButton} type="button">
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

        <section className={styles.reactionList} aria-label="Logged reactions">
          {reactionEntries.map((entry) => (
            <button className={styles.reactionCard} key={entry.id} type="button">
              <span
                className={[styles.reactionDot, styles[`reactionDot${entry.tone}`]].join(" ")}
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
                  {entry.product} · {entry.date}
                </p>
              </div>
              <span className={styles.severityBadge}>{entry.severity}</span>
              <span className={styles.chevron} aria-hidden="true" />
            </button>
          ))}
        </section>
      </div>

    </>
  );
}

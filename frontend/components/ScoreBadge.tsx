"use client";

import styles from "./ScoreBadge.module.css";

export type ScoreBadgeProps = {
  score: number;
  excluded?: boolean;
  hasWarnings?: boolean;
};

export function ScoreBadge({
  score,
  excluded = false,
  hasWarnings = false,
}: ScoreBadgeProps) {
  const className = [
    styles.badge,
    excluded ? styles.excluded : "",
    hasWarnings && !excluded ? styles.cautioned : "",
  ]
    .filter(Boolean)
    .join(" ");

  const label = excluded ? "Avoid" : hasWarnings ? "Caution" : "Match";

  return (
    <div
      className={className}
      title={`Score: ${score.toFixed(1)}`}
      aria-label={`${label}, score ${score.toFixed(1)}`}
      role="img"
    >
      <span className={styles.score}>{score.toFixed(0)}</span>
      <span className={styles.label}>{label}</span>
    </div>
  );
}

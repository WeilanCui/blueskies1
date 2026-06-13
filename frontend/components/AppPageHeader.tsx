import type { ReactNode } from "react";

import styles from "./AppPageHeader.module.css";

type AppPageHeaderProps = {
  title: string;
  description: string;
  action?: ReactNode;
};

export function AppPageHeader({ title, description, action }: AppPageHeaderProps) {
  return (
    <section className={styles.header}>
      <div className={styles.copy}>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.description}>{description}</p>
      </div>
      {action ? <div className={styles.action}>{action}</div> : null}
    </section>
  );
}

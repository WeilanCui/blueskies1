import type { ReactNode } from "react";

import styles from "./AppShell.module.css";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return <main className={styles.shell}>{children}</main>;
}

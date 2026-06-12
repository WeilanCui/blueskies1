import Link from "next/link";

import styles from "./AppTabNav.module.css";

type AppTabNavProps = {
  active: "home" | "scan" | "intake" | "catalog";
};

const tabs = [
  { id: "home", label: "Home", href: "/home" },
  { id: "scan", label: "Scan", href: "/scan" },
  { id: "intake", label: "Intake", href: "/intake" },
  { id: "catalog", label: "Catalog", href: "/skincareApi" },
] as const;

export function AppTabNav({ active }: AppTabNavProps) {
  return (
    <nav className={styles.tabNav} aria-label="App navigation">
      <div className={styles.tabList}>
        {tabs.map((tab) => (
          <Link
            aria-current={active === tab.id ? "page" : undefined}
            className={
              active === tab.id
                ? [styles.tabLink, styles.tabLinkActive].join(" ")
                : styles.tabLink
            }
            href={tab.href}
            key={tab.id}
          >
            {tab.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}

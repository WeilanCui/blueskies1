import Link from "next/link";
import { HomeIcon, MagnifyingGlassIcon, SunIcon, PresentationChartBarIcon, SparklesIcon } from '@heroicons/react/24/outline'

import styles from "./AppTabNav.module.css";

type AppTabNavProps = {
  active: "home" | "scan" | "intake" | "catalog" | "routine" | "reactions" | "forYou";
};

const tabs = [
  { id: "home", label: "Home", href: "/home", icon: HomeIcon },
  { id: "scan", label: "Products", href: "/scan", icon: MagnifyingGlassIcon },
  { id: "routine", label: "Routine", href: "/routine", icon: SunIcon },
  { id: "reactions", label: "Reactions", href: "/home", icon: PresentationChartBarIcon },
  { id: "forYou", label: "For You", href: "/skincareApi", icon: SparklesIcon },
] as const;

export function AppTabNav({ active }: AppTabNavProps) {
  return (
    <nav className={styles.tabNav} aria-label="App navigation">
      <div className={styles.tabList}>
        {tabs.map((tab) => {
          const Icon = tab.icon;

          return (
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
              <Icon aria-hidden="true" className={styles.tabIcon} />
              <span>{tab.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

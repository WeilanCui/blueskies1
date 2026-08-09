import {
  HomeIcon,
  MagnifyingGlassIcon,
  PresentationChartBarIcon,
  SparklesIcon,
  SunIcon,
} from "@heroicons/react/24/outline";
import Link from "next/link";

import styles from "./AppTabNav.module.css";

export type AppTabNavActive =
  | "home"
  | "scan"
  | "intake"
  | "catalog"
  | "routine"
  | "reactions"
  | "forYou";

type AppTabNavProps = {
  active: AppTabNavActive;
};

const tabs = [
  { id: "home", label: "Home", href: "/home", icon: HomeIcon },
  { id: "scan", label: "Products", href: "/scan", icon: MagnifyingGlassIcon },
  { id: "routine", label: "Routine", href: "/routine", icon: SunIcon },
  {
    id: "reactions",
    label: "Reactions",
    href: "/reactions",
    icon: PresentationChartBarIcon,
  },
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

"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { AppChrome } from "./AppChrome";
import { AppShell } from "./AppShell";
import type { AppTabNavActive } from "./AppTabNav";

type AppFrameProps = {
  children: ReactNode;
};

const appRoutes: Array<{ prefix: string; active: AppTabNavActive }> = [
  { prefix: "/home", active: "home" },
  { prefix: "/profile", active: "home" },
  { prefix: "/scan", active: "scan" },
  { prefix: "/routine", active: "routine" },
  { prefix: "/reactions", active: "reactions" },
  { prefix: "/intake", active: "intake" },
];

export function AppFrame({ children }: AppFrameProps) {
  const pathname = usePathname();
  const route = appRoutes.find(
    (item) =>
      pathname === item.prefix || pathname.startsWith(`${item.prefix}/`),
  );

  if (!route) {
    return children;
  }

  return (
    <AppShell>
      <AppChrome active={route.active} />
      {children}
    </AppShell>
  );
}

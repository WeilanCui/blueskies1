"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { logout } from "../lib/appApi";
import { AppTabNav, type AppTabNavActive } from "./AppTabNav";
import { Button } from "./Button";
import styles from "./AppChrome.module.css";

type AppChromeProps = {
  active: AppTabNavActive;
};

export function AppChrome({ active }: AppChromeProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const logoutMutation = useMutation({
    mutationFn: logout,
    onSettled: () => {
      queryClient.clear();
      router.replace("/login");
    },
  });

  return (
    <div className={styles.chrome}>
      <nav className={styles.appHeader}>
        <Link className={styles.appBrand} href="/home">
          <span className={styles.brandMark} aria-hidden="true" />
          <span>Blueskies</span>
        </Link>
        <Button
          className={styles.headerButton}
          type="button"
          variant="ghost"
          isDisabled={logoutMutation.isPending}
          onPress={() => logoutMutation.mutate()}
        >
          Log out
        </Button>
      </nav>
      <div className={styles.appNav}>
        <AppTabNav active={active} />
      </div>
    </div>
  );
}

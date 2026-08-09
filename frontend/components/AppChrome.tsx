"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { type AuthUser, getMe, logout } from "../lib/appApi";
import styles from "./AppChrome.module.css";
import { AppTabNav, type AppTabNavActive } from "./AppTabNav";
import { Button } from "./Button";

type AppChromeProps = {
  active: AppTabNavActive;
};

function getProfileName(user: AuthUser | undefined): string {
  return (
    user?.display_name?.trim() ||
    user?.username?.trim() ||
    user?.email?.trim() ||
    "Profile"
  );
}

function getInitials(user: AuthUser | undefined): string {
  const source = getProfileName(user);
  const [namePart] = source.split("@");
  const words = namePart
    .replaceAll(".", " ")
    .replaceAll("_", " ")
    .split(/\s+/)
    .filter(Boolean);

  if (words.length === 0) {
    return "U";
  }

  return words
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase())
    .join("");
}

export function AppChrome({ active }: AppChromeProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
  });
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
        <div className={styles.brandCluster}>
          <Link
            aria-label={`Open profile for ${getProfileName(meQuery.data?.user)}`}
            className={styles.profileAvatar}
            href="/profile"
          >
            {getInitials(meQuery.data?.user)}
          </Link>
          <Link className={styles.appBrand} href="/home">
            Blueskies
          </Link>
        </div>
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

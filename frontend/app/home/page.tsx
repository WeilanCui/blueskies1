"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppTabNav } from "../../components/AppTabNav";
import { Button } from "../../components/Button";
import { getIntake, getMe, logout } from "../../lib/appApi";
import styles from "./home.module.css";

const authFreshMs = 5 * 60 * 1000;

const skinTypeLabels: Record<string, string> = {
  combination: "Combination",
  dry: "Dry",
  normal: "Normal",
  oily: "Oily",
  sensitive: "Sensitive",
  unknown: "Not sure",
};

const fitzpatrickLabels: Record<string, string> = {
  not_provided: "Not provided",
  type_i: "Type I",
  type_ii: "Type II",
  type_iii: "Type III",
  type_iv: "Type IV",
  type_v: "Type V",
  type_vi: "Type VI",
};

function displayName(name: string, fallback: string): string {
  return name.trim() || fallback;
}

export default function HomePage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
    staleTime: authFreshMs,
  });
  const intakeQuery = useQuery({
    queryKey: ["intake"],
    queryFn: getIntake,
    enabled: meQuery.isSuccess,
    retry: false,
  });
  const logoutMutation = useMutation({
    mutationFn: logout,
    onSettled: () => {
      queryClient.clear();
      router.replace("/login");
    },
  });

  useEffect(() => {
    if (meQuery.isError) {
      router.replace("/login");
    }
  }, [meQuery.isError, router]);

  if (meQuery.isLoading || meQuery.isError || !meQuery.data) {
    return (
      <main className={styles.homeShell}>
        <p className="detail-muted">Loading your session...</p>
      </main>
    );
  }

  const user = meQuery.data.user;
  const skinProfile = intakeQuery.data?.skin_profile;
  const sensitivities = intakeQuery.data?.sensitivities ?? [];
  const firstName = displayName(user.display_name, user.username).split(" ")[0];

  return (
    <main className={styles.homeShell}>
      <nav className={["topbar", styles.homeTopbar].join(" ")}>
        <Link className="brand" href="/">
          Blueskies
        </Link>
        <div className="topbar-actions">
          <Button
            type="button"
            variant="ghost"
            isDisabled={logoutMutation.isPending}
            onPress={() => logoutMutation.mutate()}
          >
            Log out
          </Button>
        </div>
      </nav>
      <AppTabNav active="home" />

      <div className={styles.homeLayout}>
        <section className={styles.homeHero}>
          <div className={styles.homeHeroCopy}>
            <p className="landing-eyebrow">Your home</p>
            <h1>{firstName}'s skin profile</h1>
            <p>
              Your intake is saved. This is the starting point for regimen
              tracking, product scans, and personalized product fit.
            </p>
            <div className={styles.homeHeroActions}>
              <Link href="/intake">
                <Button type="button">Edit profile</Button>
              </Link>
              <Link href="/skincareApi">
                <Button type="button" variant="secondary">
                  Browse catalog
                </Button>
              </Link>
            </div>
          </div>

          <div className={styles.summaryGrid}>
            <div className={styles.summaryCard}>
              <span>Skin type</span>
              <strong>
                {skinProfile
                  ? skinTypeLabels[skinProfile.skin_type] || skinProfile.skin_type
                  : "Not saved"}
              </strong>
            </div>
            <div className={styles.summaryCard}>
              <span>Fitzpatrick</span>
              <strong>
                {skinProfile
                  ? fitzpatrickLabels[skinProfile.fitzpatrick_skin_type] ||
                  skinProfile.fitzpatrick_skin_type
                  : "Not saved"}
              </strong>
            </div>
            <div className={styles.summaryCard}>
              <span>Sensitivity</span>
              <strong>
                {skinProfile?.baseline_sensitivity === null ||
                  skinProfile?.baseline_sensitivity === undefined
                  ? "Not saved"
                  : `${skinProfile.baseline_sensitivity}/10`}
              </strong>
            </div>
            <div className={styles.summaryCard}>
              <span>Concerns</span>
              <strong>{skinProfile?.primary_concerns.length ?? 0}</strong>
            </div>
          </div>
        </section>

        <section className={styles.sectionGrid}>
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <h2>Current profile</h2>
              <p>{skinProfile?.routine_notes || "No routine notes yet."}</p>
            </div>
            {skinProfile ? (
              <>
                <div className={styles.tagList}>
                  {skinProfile.primary_concerns.map((concern) => (
                    <span className="tag" key={concern}>
                      {concern.replaceAll("_", " ")}
                    </span>
                  ))}
                  {skinProfile.goals.map((goal) => (
                    <span className="chip" key={goal}>
                      {goal}
                    </span>
                  ))}
                </div>
                {sensitivities.length > 0 && (
                  <div className={styles.tagList}>
                    {sensitivities.map((item) => (
                      <span className="badge" key={item}>
                        {item}
                      </span>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className={styles.emptyState}>
                <p>No intake has been saved yet.</p>
                <Link href="/intake">
                  <Button type="button">Start intake</Button>
                </Link>
              </div>
            )}
          </div>

          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <h2>Next</h2>
            </div>
            <div className={styles.statusList}>
              <div className={styles.statusItem}>
                <div>
                  <strong>Regimen</strong>
                  <span>Products and routine history</span>
                </div>
                <span className={styles.soonBadge}>Soon</span>
              </div>
              <div className={styles.statusItem}>
                <div>
                  <strong>Product scan</strong>
                  <span>Barcode and ingredient lookup</span>
                </div>
                <span className={styles.soonBadge}>Soon</span>
              </div>
              <div className={styles.statusItem}>
                <div>
                  <strong>Skin log</strong>
                  <span>Check-ins and change tracking</span>
                </div>
                <span className={styles.soonBadge}>Soon</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

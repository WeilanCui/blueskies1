"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppChrome } from "../../components/AppChrome";
import { Button } from "../../components/Button";
import { getIntake, getMe } from "../../lib/appApi";
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

function formatToken(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export default function HomePage() {
  const router = useRouter();

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
  const primaryConcerns = skinProfile?.primary_concerns ?? [];
  const goals = skinProfile?.goals ?? [];
  const signalCount = [
    skinProfile?.skin_type,
    skinProfile?.fitzpatrick_skin_type &&
      skinProfile.fitzpatrick_skin_type !== "not_provided",
    skinProfile?.baseline_sensitivity !== null &&
      skinProfile?.baseline_sensitivity !== undefined,
    primaryConcerns.length > 0,
    goals.length > 0,
    sensitivities.length > 0,
  ].filter(Boolean).length;
  const profileVitals = [
    {
      label: "Skin type",
      value: skinProfile
        ? skinTypeLabels[skinProfile.skin_type] || skinProfile.skin_type
        : "Not saved",
    },
    {
      label: "Fitzpatrick",
      value: skinProfile
        ? fitzpatrickLabels[skinProfile.fitzpatrick_skin_type] ||
          skinProfile.fitzpatrick_skin_type
        : "Not saved",
    },
    {
      label: "Sensitivity",
      value:
        skinProfile?.baseline_sensitivity === null ||
        skinProfile?.baseline_sensitivity === undefined
          ? "Not saved"
          : `${skinProfile.baseline_sensitivity}/10`,
    },
  ];
  const nextCards = [
    {
      title: "Scan a product",
      text: "Capture a barcode, product front, or ingredient list from your phone.",
      href: "/scan",
      action: "Open scan",
    },
    {
      title: "Review catalog",
      text: "Browse ingredients and product data while matching logic comes online.",
      href: "/skincareApi",
      action: "Browse",
    },
  ];

  return (
    <main className={styles.homeShell}>
      <AppChrome active="home" />

      <div className={styles.homeLayout}>
        <section className={styles.welcomePanel}>
          <div className={styles.welcomeCopy}>
            <div className={styles.todayRow}>
              <span>Today</span>
              <strong>Skin dashboard</strong>
            </div>
            <h1>Hi, {firstName}</h1>
            <p>
              Your saved context is ready for product scans, routine tracking,
              and ingredient fit checks as the app grows.
            </p>
          </div>
          <div className={styles.profileSignalCard}>
            <div className={styles.signalHeader}>
              <span>Personal context</span>
              <strong>{signalCount}/6 signals</strong>
            </div>
            <div className={styles.signalTrack} aria-hidden="true">
              {Array.from({ length: 6 }, (_, index) => (
                <span
                  className={
                    index < signalCount
                      ? [styles.signalSegment, styles.signalSegmentActive].join(" ")
                      : styles.signalSegment
                  }
                  key={index}
                />
              ))}
            </div>
            <p>
              Used to personalize future product and regimen analysis. Medical
              concerns still belong with a clinician.
            </p>
          </div>
        </section>

        <section className={styles.dashboardGrid}>
          <div className={styles.primaryColumn}>
            <section className={styles.scanCard}>
              <div className={styles.scanVisual} aria-hidden="true">
                <span className={styles.scanRing} />
                <span className={styles.scanLine} />
                <span className={styles.scanDotOne} />
                <span className={styles.scanDotTwo} />
              </div>
              <div className={styles.scanCopy}>
                <p className="landing-eyebrow">Next action</p>
                <h2>Scan what you are using.</h2>
                <p>
                  Add a product, barcode, ingredient list, or skin-progress
                  photo. This is the main entry point for regimen intelligence.
                </p>
              </div>
              <Link className={styles.actionLink} href="/scan">
                <Button className={styles.actionButton} type="button">
                  Scan or upload
                </Button>
              </Link>
            </section>

            <section className={styles.timelinePanel}>
              <div className={styles.panelHeader}>
                <div>
                  <span>Skin log</span>
                  <h2>Track changes over time.</h2>
                </div>
                <span className={styles.soonBadge}>Soon</span>
              </div>
              <div className={styles.timelineList}>
                <div className={styles.timelineItem}>
                  <span className={styles.timelineMarker} />
                  <div>
                    <strong>Morning check-in</strong>
                    <p>Redness, dryness, breakouts, oil, and texture notes.</p>
                  </div>
                </div>
                <div className={styles.timelineItem}>
                  <span className={styles.timelineMarker} />
                  <div>
                    <strong>Product effect</strong>
                    <p>Connect a skin change to routine use and timing.</p>
                  </div>
                </div>
                <div className={styles.timelineItem}>
                  <span className={styles.timelineMarker} />
                  <div>
                    <strong>Context layer</strong>
                    <p>Weather, location, hormones, and lifestyle signals.</p>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <aside className={styles.sideColumn}>
            <section className={styles.profilePanel}>
              <div className={styles.panelHeader}>
                <div>
                  <span>Profile snapshot</span>
                  <h2>Current baseline</h2>
                </div>
              </div>
              <div className={styles.vitalList}>
                {profileVitals.map((item) => (
                  <div className={styles.vitalItem} key={item.label}>
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                  </div>
                ))}
              </div>
              <div className={styles.tagList}>
                {primaryConcerns.length > 0 ? (
                  primaryConcerns.slice(0, 6).map((concern) => (
                    <span className="tag" key={concern}>
                      {formatToken(concern)}
                    </span>
                  ))
                ) : (
                  <span className="tag">No concerns saved</span>
                )}
              </div>
            </section>

            <section className={styles.regimenPanel}>
              <div className={styles.panelHeader}>
                <div>
                  <span>Regimen intelligence</span>
                  <h2>What Blueskies will connect</h2>
                </div>
              </div>
              <div className={styles.connectionList}>
                <div>
                  <strong>Products</strong>
                  <span>Formulations, ingredients, and barcodes</span>
                </div>
                <div>
                  <strong>Fit</strong>
                  <span>Goals, constraints, and sensitivities</span>
                </div>
                <div>
                  <strong>Outcomes</strong>
                  <span>Skin state before and after routine changes</span>
                </div>
              </div>
            </section>
          </aside>
        </section>

        <section className={styles.nextGrid}>
          {nextCards.map((card) => (
            <Link className={styles.nextCard} href={card.href} key={card.title}>
              <div>
                <h2>{card.title}</h2>
                <p>{card.text}</p>
              </div>
              <span>{card.action}</span>
            </Link>
          ))}
        </section>

        <section className={styles.notesPanel}>
          <div className={styles.panelHeader}>
            <div>
              <span>Saved notes</span>
              <h2>Routine context</h2>
            </div>
          </div>
          <p>{skinProfile?.routine_notes || "No routine notes have been added yet."}</p>
          <div className={styles.tagList}>
            {goals.length > 0 ? (
              goals.slice(0, 4).map((goal) => (
                <span className="chip" key={goal}>
                  {goal}
                </span>
              ))
            ) : (
              <span className="chip">No goals saved</span>
            )}
            {sensitivities.length > 0 &&
              sensitivities.slice(0, 4).map((item) => (
                <span className="badge" key={item}>
                  {item}
                </span>
              ))}
          </div>
        </section>
      </div>

      <div className={styles.mobileActionDock}>
        <Link href="/scan">
          <Button className={styles.mobileDockButton} type="button">
            Scan or upload
          </Button>
        </Link>
      </div>
    </main>
  );
}

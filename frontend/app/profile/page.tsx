"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Button } from "../../components/Button";
import { getIntake, getMe, type AuthUser } from "../../lib/appApi";
import styles from "./profile.module.css";

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

function profileName(user: AuthUser): string {
  return user.display_name?.trim() || user.username || user.email || "Profile";
}

function initialsFor(user: AuthUser): string {
  const [namePart] = profileName(user).split("@");
  const words = namePart
    .replaceAll(".", " ")
    .replaceAll("_", " ")
    .split(/\s+/)
    .filter(Boolean);

  return (
    words
      .slice(0, 2)
      .map((word) => word[0]?.toUpperCase())
      .join("") || "U"
  );
}

function formatToken(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export default function ProfilePage() {
  const router = useRouter();
  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
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
    return <p className="detail-muted">Loading your session...</p>;
  }

  const user = meQuery.data.user;
  const skinProfile = intakeQuery.data?.skin_profile;
  const sensitivities = intakeQuery.data?.sensitivities ?? [];
  const vitals = [
    {
      label: "Skin type",
      value: skinProfile
        ? skinTypeLabels[skinProfile.skin_type] || formatToken(skinProfile.skin_type)
        : "Not saved",
    },
    {
      label: "Fitzpatrick",
      value: skinProfile
        ? fitzpatrickLabels[skinProfile.fitzpatrick_skin_type] ||
          formatToken(skinProfile.fitzpatrick_skin_type)
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

  return (
    <main className={styles.profileLayout}>
      <section className={styles.profileHero}>
        <div className={styles.avatar} aria-hidden="true">
          {initialsFor(user)}
        </div>
        <div className={styles.heroCopy}>
          <p className="landing-eyebrow">My Profile</p>
          <h1>My Profile</h1>
          <p>{profileName(user)}</p>
        </div>
        <Link className={styles.editLink} href="/intake">
          <Button type="button" variant="ghost">
            Edit profile
          </Button>
        </Link>
      </section>

      <section className={styles.profileGrid}>
        <article className={styles.profilePanel}>
          <div className={styles.panelHeader}>
            <span>Skin baseline</span>
            <h2>Current profile</h2>
          </div>
          <div className={styles.vitalList}>
            {vitals.map((item) => (
              <div className={styles.vitalItem} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className={styles.profilePanel}>
          <div className={styles.panelHeader}>
            <span>Focus areas</span>
            <h2>Concerns and goals</h2>
          </div>
          <div className={styles.tagList}>
            {(skinProfile?.primary_concerns ?? []).length > 0 ? (
              skinProfile?.primary_concerns.map((concern) => (
                <span className="tag" key={concern}>
                  {formatToken(concern)}
                </span>
              ))
            ) : (
              <span className="tag">No concerns saved</span>
            )}
          </div>
          <div className={styles.tagList}>
            {(skinProfile?.goals ?? []).length > 0 ? (
              skinProfile?.goals.map((goal) => (
                <span className="chip" key={goal}>
                  {goal}
                </span>
              ))
            ) : (
              <span className="chip">No goals saved</span>
            )}
          </div>
        </article>

        <article className={styles.profilePanel}>
          <div className={styles.panelHeader}>
            <span>Avoid list</span>
            <h2>Sensitivities</h2>
          </div>
          <div className={styles.tagList}>
            {sensitivities.length > 0 ? (
              sensitivities.map((item) => (
                <span className="badge" key={item}>
                  {item}
                </span>
              ))
            ) : (
              <span className="badge">No sensitivities saved</span>
            )}
          </div>
        </article>

        <article className={styles.profilePanel}>
          <div className={styles.panelHeader}>
            <span>Routine context</span>
            <h2>Saved notes</h2>
          </div>
          <p className={styles.notes}>
            {skinProfile?.routine_notes || "No routine notes have been added yet."}
          </p>
        </article>
      </section>
    </main>
  );
}

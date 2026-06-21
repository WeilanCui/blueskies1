"use client";

import {
  ArrowLeftIcon,
  PencilSquareIcon,
  PlusIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "../../components/Button";
import {
  getIntake,
  getMe,
  saveIntake,
  updateMe,
  type AuthResponse,
  type AuthUser,
  type IntakePayload,
  type IntakeResponse,
} from "../../lib/appApi";
import styles from "./profile.module.css";

type EditableSection = "identity" | "skinType" | "goal" | "concerns" | "avoid";

const skinTypes = [
  ["dry", "Dry"],
  ["oily", "Oily"],
  ["combination", "Combination"],
  ["normal", "Normal"],
  ["sensitive", "Sensitive"],
  ["unknown", "Not sure"],
];

const concernSections = [
  {
    title: "Breakouts & congestion",
    items: [
      ["acne", "Acne"],
      ["clogged_pores", "Clogged pores"],
      ["blackheads", "Blackheads"],
      ["whiteheads", "Whiteheads"],
    ],
  },
  {
    title: "Sensitivity & inflammation",
    items: [
      ["redness", "Redness"],
      ["stinging", "Stinging or burning"],
      ["reactive_skin", "Reactive skin"],
      ["rosacea_prone", "Rosacea-prone"],
    ],
  },
  {
    title: "Hydration & barrier",
    items: [
      ["dryness", "Dryness"],
      ["dehydration", "Dehydration"],
      ["flaking", "Flaking"],
      ["tightness", "Tightness"],
      ["barrier_damage", "Barrier damage"],
    ],
  },
  {
    title: "Oil & pores",
    items: [
      ["oiliness", "Oiliness"],
      ["enlarged_pores", "Enlarged pores"],
      ["shine", "Shine"],
      ["sebaceous_filaments", "Sebaceous filaments"],
    ],
  },
  {
    title: "Tone & pigment",
    items: [
      ["dark_spots", "Dark spots"],
      ["hyperpigmentation", "Hyperpigmentation"],
      ["melasma_prone", "Melasma-prone"],
      ["post_acne_marks", "Post-acne marks"],
    ],
  },
  {
    title: "Texture & dullness",
    items: [
      ["roughness", "Roughness"],
      ["bumps", "Bumps"],
      ["uneven_texture", "Uneven texture"],
      ["dullness", "Dullness"],
    ],
  },
  {
    title: "Aging & firmness",
    items: [
      ["fine_lines", "Fine lines"],
      ["wrinkles", "Wrinkles"],
      ["loss_of_firmness", "Loss of firmness"],
    ],
  },
  {
    title: "Eye area",
    items: [
      ["dark_circles", "Dark circles"],
      ["puffiness", "Puffiness"],
      ["eye_fine_lines", "Eye-area fine lines"],
    ],
  },
];

const sensitivityOptions = [
  "Fragrance",
  "Essential oils",
  "Denatured alcohol",
  "Retinoids",
  "AHAs / BHAs",
  "Benzoyl peroxide",
  "Sulfates",
  "Lanolin",
];

const skinTypeLabels = Object.fromEntries(skinTypes);

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

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

function cleanList(values: string[]): string[] {
  const seen = new Set<string>();
  const cleaned: string[] = [];
  for (const item of values) {
    const value = item.trim();
    const key = value.toLowerCase();
    if (!value || seen.has(key)) {
      continue;
    }
    seen.add(key);
    cleaned.push(value);
  }
  return cleaned;
}

function intakeToPayload(
  intake: IntakeResponse | undefined,
  overrides: Partial<IntakePayload> = {},
): IntakePayload {
  const skinProfile = intake?.skin_profile;
  const skinTypes = getSavedSkinTypes(skinProfile);

  return {
    skin_type: skinProfile?.skin_type ?? "unknown",
    skin_types: skinTypes.length > 0 ? skinTypes : [skinProfile?.skin_type ?? "unknown"],
    fitzpatrick_skin_type: skinProfile?.fitzpatrick_skin_type ?? "not_provided",
    baseline_sensitivity: skinProfile?.baseline_sensitivity ?? null,
    primary_concerns: skinProfile?.primary_concerns ?? [],
    goals: skinProfile?.goals ?? [],
    goals_text: "",
    pregnancy_status: skinProfile?.pregnancy_status ?? "not_provided",
    climate: skinProfile?.climate ?? "",
    routine_notes: skinProfile?.routine_notes ?? "",
    sensitivities: intake?.sensitivities ?? [],
    ...overrides,
  };
}

function getSavedSkinTypes(
  skinProfile: IntakeResponse["skin_profile"] | undefined,
): string[] {
  if (!skinProfile) {
    return [];
  }
  if (skinProfile.skin_types?.length > 0) {
    return skinProfile.skin_types;
  }
  return skinProfile.skin_type ? [skinProfile.skin_type] : [];
}

function Section({
  section,
  title,
  children,
  editingSection,
  onEdit,
  editor,
}: {
  section: EditableSection;
  title: string;
  children: React.ReactNode;
  editingSection: EditableSection | null;
  onEdit: (section: EditableSection) => void;
  editor: React.ReactNode;
}) {
  const isEditing = editingSection === section;

  return (
    <article className={styles.profileSection}>
      <div className={styles.sectionHeader}>
        <h2>{title}</h2>
        <button
          aria-label={`Edit ${title.toLowerCase()}`}
          className={styles.iconButton}
          type="button"
          onClick={() => onEdit(section)}
        >
          <PencilSquareIcon aria-hidden="true" />
        </button>
      </div>
      {isEditing ? editor : <div className={styles.sectionDisplay}>{children}</div>}
    </article>
  );
}

export default function ProfilePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [editingSection, setEditingSection] = useState<EditableSection | null>(null);
  const [displayNameDraft, setDisplayNameDraft] = useState("");
  const [skinTypesDraft, setSkinTypesDraft] = useState<string[]>([]);
  const [goalDraft, setGoalDraft] = useState("");
  const [concernsDraft, setConcernsDraft] = useState<string[]>([]);
  const [sensitivitiesDraft, setSensitivitiesDraft] = useState<string[]>([]);
  const [customSensitivity, setCustomSensitivity] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  const identityMutation = useMutation({
    mutationFn: updateMe,
    onSuccess: (data) => {
      queryClient.setQueryData<AuthResponse>(["me"], data);
      setEditingSection(null);
      setMessage("Profile updated.");
      setError(null);
    },
    onError: (updateError) => {
      setError(
        updateError instanceof Error ? updateError.message : "Could not update your profile.",
      );
      setMessage(null);
    },
  });

  const intakeMutation = useMutation({
    mutationFn: saveIntake,
    onSuccess: (data) => {
      queryClient.setQueryData<IntakeResponse>(["intake"], data);
      queryClient.setQueryData<AuthResponse | undefined>(["me"], (current) =>
        current
          ? {
              user: {
                ...current.user,
                has_completed_intake: true,
              },
            }
          : current,
      );
      setEditingSection(null);
      setMessage("Profile section saved.");
      setError(null);
    },
    onError: (saveError) => {
      setError(saveError instanceof Error ? saveError.message : "Could not save this section.");
      setMessage(null);
    },
  });

  useEffect(() => {
    if (meQuery.isError) {
      router.replace("/login");
    }
  }, [meQuery.isError, router]);

  function openEditor(section: EditableSection) {
    const user = meQuery.data?.user;
    const skinProfile = intakeQuery.data?.skin_profile;
    setDisplayNameDraft(user ? profileName(user) : "");
    setSkinTypesDraft(getSavedSkinTypes(skinProfile));
    setGoalDraft(skinProfile?.goals[0] ?? "");
    setConcernsDraft(skinProfile?.primary_concerns ?? []);
    setSensitivitiesDraft(intakeQuery.data?.sensitivities ?? []);
    setCustomSensitivity("");
    setMessage(null);
    setError(null);
    setEditingSection(section);
  }

  function cancelEditing() {
    setEditingSection(null);
    setCustomSensitivity("");
    setError(null);
  }

  function saveIdentity(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    identityMutation.mutate({ display_name: displayNameDraft });
  }

  function saveIntakeSection(
    event: React.FormEvent<HTMLFormElement>,
    overrides: Partial<IntakePayload>,
  ) {
    event.preventDefault();
    intakeMutation.mutate(intakeToPayload(intakeQuery.data, overrides));
  }

  function addCustomSensitivity() {
    const next = cleanList([...sensitivitiesDraft, customSensitivity]);
    setSensitivitiesDraft(next);
    setCustomSensitivity("");
  }

  if (meQuery.isLoading || meQuery.isError || !meQuery.data) {
    return <p className="detail-muted">Loading your session...</p>;
  }

  const user = meQuery.data.user;
  const skinProfile = intakeQuery.data?.skin_profile;
  const sensitivities = intakeQuery.data?.sensitivities ?? [];
  const isSaving = identityMutation.isPending || intakeMutation.isPending;
  const primaryGoal = skinProfile?.goals[0] ?? "";
  const savedSkinTypes = getSavedSkinTypes(skinProfile);
  const savedSkinTypeLabel =
    savedSkinTypes.length > 0
      ? savedSkinTypes
          .map((skinType) => skinTypeLabels[skinType] || formatToken(skinType))
          .join(", ")
      : "";
  const profileSubtitle = [
    savedSkinTypeLabel ? `${savedSkinTypeLabel} skin` : "Skin profile",
    primaryGoal,
  ]
    .filter(Boolean)
    .join(" - ");

  return (
    <main className={styles.profileLayout}>
      <header className={styles.pageHeader}>
        <button
          aria-label="Go back"
          className={styles.backButton}
          type="button"
          onClick={() => router.back()}
        >
          <ArrowLeftIcon aria-hidden="true" />
        </button>
        <h1>My Profile</h1>
      </header>

      <section className={[styles.profileSection, styles.identitySection].join(" ")}>
        <div className={styles.identitySummary}>
          <div className={styles.avatar} aria-hidden="true">
            {initialsFor(user)}
          </div>
          <div className={styles.identityCopy}>
            <strong>{profileName(user)}</strong>
            <span>{profileSubtitle || "No skin profile saved yet"}</span>
          </div>
          <button
            aria-label="Edit profile identity"
            className={styles.iconButton}
            type="button"
            onClick={() => openEditor("identity")}
          >
            <PencilSquareIcon aria-hidden="true" />
          </button>
        </div>
        {editingSection === "identity" && (
          <form className={styles.editor} onSubmit={saveIdentity}>
            <label className={styles.field}>
              <span>Display name</span>
              <input
                maxLength={128}
                type="text"
                value={displayNameDraft}
                onChange={(event) => setDisplayNameDraft(event.target.value)}
              />
            </label>
            <div className={styles.editorActions}>
              <Button type="submit" isDisabled={isSaving}>
                {identityMutation.isPending ? "Saving..." : "Save"}
              </Button>
              <Button type="button" variant="ghost" onPress={cancelEditing}>
                Cancel
              </Button>
            </div>
          </form>
        )}
      </section>

      <section className={styles.profileGrid}>
        <Section
          section="skinType"
          title="Skin type"
          editingSection={editingSection}
          onEdit={openEditor}
          editor={
            <form
              className={styles.editor}
              onSubmit={(event) => {
                const selectedSkinTypes =
                  skinTypesDraft.length > 0 ? skinTypesDraft : ["unknown"];
                saveIntakeSection(event, {
                  skin_type: selectedSkinTypes[0],
                  skin_types: selectedSkinTypes,
                });
              }}
            >
              <div className={styles.skinTypeRows}>
                {skinTypes.map(([value, label]) => (
                  <label className={styles.skinTypeOption} key={value}>
                    <input
                      checked={skinTypesDraft.includes(value)}
                      type="checkbox"
                      value={value}
                      onChange={() =>
                        setSkinTypesDraft((current) => toggleValue(current, value))
                      }
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
              <div className={styles.editorActions}>
                <Button type="submit" isDisabled={isSaving}>
                  {intakeMutation.isPending ? "Saving..." : "Save"}
                </Button>
                <Button type="button" variant="ghost" onPress={cancelEditing}>
                  Cancel
                </Button>
              </div>
            </form>
          }
        >
          {savedSkinTypes.length > 0 ? (
            <div className={styles.tagList}>
              {savedSkinTypes.map((skinType) => (
                <span className={styles.valuePill} key={skinType}>
                  {skinTypeLabels[skinType] || formatToken(skinType)}
                </span>
              ))}
            </div>
          ) : (
            <span className={styles.valuePill}>Not saved</span>
          )}
        </Section>

        <Section
          section="goal"
          title="Primary goal"
          editingSection={editingSection}
          onEdit={openEditor}
          editor={
            <form
              className={styles.editor}
              onSubmit={(event) =>
                saveIntakeSection(event, {
                  goals: goalDraft.trim() ? [goalDraft.trim()] : [],
                  goals_text: "",
                })
              }
            >
              <label className={styles.field}>
                <span>Primary goal</span>
                <textarea
                  rows={3}
                  value={goalDraft}
                  onChange={(event) => setGoalDraft(event.target.value)}
                />
              </label>
              <div className={styles.editorActions}>
                <Button type="submit" isDisabled={isSaving}>
                  {intakeMutation.isPending ? "Saving..." : "Save"}
                </Button>
                <Button type="button" variant="ghost" onPress={cancelEditing}>
                  Cancel
                </Button>
              </div>
            </form>
          }
        >
          <span className={styles.goalPill}>{primaryGoal || "No goal saved"}</span>
        </Section>

        <Section
          section="concerns"
          title="Skin concerns"
          editingSection={editingSection}
          onEdit={openEditor}
          editor={
            <form
              className={styles.editor}
              onSubmit={(event) =>
                saveIntakeSection(event, { primary_concerns: concernsDraft })
              }
            >
              <div className={styles.concernStack}>
                {concernSections.map((section) => (
                  <fieldset className={styles.fieldset} key={section.title}>
                    <legend>{section.title}</legend>
                    <div className={styles.choiceGrid}>
                      {section.items.map(([value, label]) => (
                        <label className={styles.choicePill} key={value}>
                          <input
                            checked={concernsDraft.includes(value)}
                            type="checkbox"
                            onChange={() =>
                              setConcernsDraft((current) => toggleValue(current, value))
                            }
                          />
                          <span>{label}</span>
                        </label>
                      ))}
                    </div>
                  </fieldset>
                ))}
              </div>
              <div className={styles.editorActions}>
                <Button type="submit" isDisabled={isSaving}>
                  {intakeMutation.isPending ? "Saving..." : "Save"}
                </Button>
                <Button type="button" variant="ghost" onPress={cancelEditing}>
                  Cancel
                </Button>
              </div>
            </form>
          }
        >
          <div className={styles.tagList}>
            {(skinProfile?.primary_concerns ?? []).length > 0 ? (
              skinProfile?.primary_concerns.map((concern) => (
                <span className={styles.valuePill} key={concern}>
                  {formatToken(concern)}
                </span>
              ))
            ) : (
              <span className={styles.valuePill}>No concerns saved</span>
            )}
          </div>
        </Section>

        <Section
          section="avoid"
          title="Ingredients to avoid"
          editingSection={editingSection}
          onEdit={openEditor}
          editor={
            <form
              className={styles.editor}
              onSubmit={(event) =>
                saveIntakeSection(event, { sensitivities: cleanList(sensitivitiesDraft) })
              }
            >
              <p className={styles.sectionHelp}>
                We will flag these in ingredient analysis and exclude products containing
                them from recommendations.
              </p>
              <div className={styles.choiceGrid}>
                {sensitivityOptions.map((item) => (
                  <label className={styles.choicePill} key={item}>
                    <input
                      checked={sensitivitiesDraft.includes(item)}
                      type="checkbox"
                      onChange={() =>
                        setSensitivitiesDraft((current) => toggleValue(current, item))
                      }
                    />
                    <span>{item}</span>
                  </label>
                ))}
              </div>
              <div className={styles.customAdd}>
                <input
                  type="text"
                  value={customSensitivity}
                  placeholder="e.g. Sodium Lauryl Sulfate"
                  onChange={(event) => setCustomSensitivity(event.target.value)}
                />
                <Button type="button" variant="secondary" onPress={addCustomSensitivity}>
                  <PlusIcon aria-hidden="true" />
                  Add
                </Button>
              </div>
              {sensitivitiesDraft.length > 0 && (
                <div className={styles.tagList}>
                  {sensitivitiesDraft.map((item) => (
                    <button
                      className={styles.removablePill}
                      key={item}
                      type="button"
                      onClick={() =>
                        setSensitivitiesDraft((current) =>
                          current.filter((value) => value !== item),
                        )
                      }
                    >
                      {item}
                      <XMarkIcon aria-hidden="true" />
                    </button>
                  ))}
                </div>
              )}
              <div className={styles.editorActions}>
                <Button type="submit" isDisabled={isSaving}>
                  {intakeMutation.isPending ? "Saving..." : "Save"}
                </Button>
                <Button type="button" variant="ghost" onPress={cancelEditing}>
                  Cancel
                </Button>
              </div>
            </form>
          }
        >
          <p className={styles.sectionHelp}>
            We will flag these in ingredient analysis and exclude products containing them
            from recommendations.
          </p>
          {sensitivities.length > 0 ? (
            <div className={styles.tagList}>
              {sensitivities.map((item) => (
                <span className={styles.valuePill} key={item}>
                  {item}
                </span>
              ))}
            </div>
          ) : (
            <p className={styles.emptyState}>No ingredients blocked yet.</p>
          )}
        </Section>
      </section>

      {(message || error) && (
        <div className={styles.statusRegion} role="status">
          {message && <p className="contact-success">{message}</p>}
          {error && <p className="contact-error">{error}</p>}
        </div>
      )}
    </main>
  );
}

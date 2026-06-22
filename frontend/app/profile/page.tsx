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
import { ConcernPicker } from "../../components/profile/ConcernPicker";
import { ProfileSection } from "../../components/profile/ProfileSection";
import { SensitivityOptions } from "../../components/profile/SensitivityOptions";
import { SkinTypeSelector } from "../../components/profile/SkinTypeSelector";
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
import {
  cleanList,
  concernLabels,
  formatToken,
  getSavedSkinTypes,
  intakeToPayload,
  skinTypeLabels,
  toggleValue,
} from "../../lib/profileForm";
import styles from "./profile.module.css";

type EditableSection = "identity" | "skinType" | "goal" | "concerns" | "avoid";

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
        <ProfileSection
          classNames={{
            section: styles.profileSection,
            header: styles.sectionHeader,
            iconButton: styles.iconButton,
            display: styles.sectionDisplay,
          }}
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
              <SkinTypeSelector
                multiple
                className={styles.skinTypeRows}
                name="profile_skin_types"
                optionClassName={styles.skinTypeOption}
                values={skinTypesDraft}
                onChange={setSkinTypesDraft}
              />
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
        </ProfileSection>

        <ProfileSection
          classNames={{
            section: styles.profileSection,
            header: styles.sectionHeader,
            iconButton: styles.iconButton,
            display: styles.sectionDisplay,
          }}
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
        </ProfileSection>

        <ProfileSection
          classNames={{
            section: styles.profileSection,
            header: styles.sectionHeader,
            iconButton: styles.iconButton,
            display: styles.sectionDisplay,
          }}
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
              <ConcernPicker
                classNames={{
                  stack: styles.concernStack,
                  fieldset: styles.fieldset,
                  grid: styles.choiceGrid,
                  option: styles.choicePill,
                }}
                values={concernsDraft}
                onChange={setConcernsDraft}
              />
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
                  {concernLabels[concern] || formatToken(concern)}
                </span>
              ))
            ) : (
              <span className={styles.valuePill}>No concerns saved</span>
            )}
          </div>
        </ProfileSection>

        <ProfileSection
          classNames={{
            section: styles.profileSection,
            header: styles.sectionHeader,
            iconButton: styles.iconButton,
            display: styles.sectionDisplay,
          }}
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
              <SensitivityOptions
                gridClassName={styles.choiceGrid}
                optionClassName={styles.choicePill}
                values={sensitivitiesDraft}
                onToggle={(item) =>
                  setSensitivitiesDraft((current) => toggleValue(current, item))
                }
              />
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
        </ProfileSection>
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

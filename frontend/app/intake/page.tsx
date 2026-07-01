"use client";

import { Input, Label, TextArea, TextField } from "@heroui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "../../components/Button";
import { SensitivityOptions } from "../../components/profile/SensitivityOptions";
import { SkinTypeSelector } from "../../components/profile/SkinTypeSelector";
import { useConcernZones } from "../../hooks/useConcernZones";
import {
  type AuthResponse,
  getIntake,
  getMe,
  getSkinConcerns,
  type IntakePayload,
  saveIntake,
  searchSkinConcerns,
} from "../../lib/appApi";
import {
  type FitzpatrickStyleKey,
  fitzpatrickTypeOptions,
  toggleValue,
} from "../../lib/profileForm";
import FaceMap from "../experience/FaceMap";
import styles from "./intake.module.css";

const fitzpatrickTileClasses: Record<FitzpatrickStyleKey, string> = {
  notProvided: styles.fitzpatrickTileNotProvided,
  typeI: styles.fitzpatrickTileTypeI,
  typeII: styles.fitzpatrickTileTypeII,
  typeIII: styles.fitzpatrickTileTypeIII,
  typeIV: styles.fitzpatrickTileTypeIV,
  typeV: styles.fitzpatrickTileTypeV,
  typeVI: styles.fitzpatrickTileTypeVI,
};

function useDebouncedValue(value: string, delayMs: number) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setDebouncedValue(value);
    }, delayMs);

    return () => clearTimeout(timeoutId);
  }, [value, delayMs]);

  return debouncedValue;
}

export default function IntakePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [skinType, setSkinType] = useState("combination");
  const [fitzpatrickSkinType, setFitzpatrickSkinType] =
    useState("not_provided");
  const [baselineSensitivity, setBaselineSensitivity] = useState(5);
  const [concerns, setConcerns] = useState<string[]>([]);
  const [concernSearch, setConcernSearch] = useState("");
  const [goalsText, setGoalsText] = useState("");
  const [pregnancyStatus, setPregnancyStatus] = useState("not_provided");
  const [climate, setClimate] = useState("");
  const [routineNotes, setRoutineNotes] = useState("");
  const [sensitivities, setSensitivities] = useState<string[]>([]);
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
  const concernOptionsQuery = useQuery({
    queryKey: ["skin-concerns"],
    queryFn: getSkinConcerns,
    enabled: meQuery.isSuccess,
  });
  const concernSearchTerm = concernSearch.trim();
  const debouncedConcernSearchTerm = useDebouncedValue(concernSearchTerm, 300);
  const concernSearchQuery = useQuery({
    queryKey: ["skin-concerns", "search", debouncedConcernSearchTerm],
    queryFn: () => searchSkinConcerns(debouncedConcernSearchTerm),
    enabled: debouncedConcernSearchTerm.length >= 2,
  });
  const isConcernSearchPending =
    concernSearchTerm.length >= 2 &&
    (concernSearchTerm !== debouncedConcernSearchTerm ||
      concernSearchQuery.isFetching);
  const saveMutation = useMutation({
    mutationFn: saveIntake,
    onSuccess: (data) => {
      queryClient.setQueryData(["intake"], data);
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
      router.replace("/home");
      setMessage("Your skin profile is saved.");
      setError(null);
    },
    onError: (saveError) => {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "Could not save intake.",
      );
      setMessage(null);
    },
  });
  useEffect(() => {
    if (meQuery.isError) {
      router.replace("/login");
    }
  }, [meQuery.isError, router]);

  useEffect(() => {
    const skinProfile = intakeQuery.data?.skin_profile;
    if (!skinProfile) {
      return;
    }
    setSkinType(skinProfile.skin_types[0] ?? "unknown");
    setFitzpatrickSkinType(skinProfile.fitzpatrick_skin_type);
    setBaselineSensitivity(skinProfile.baseline_sensitivity ?? 5);
    setConcerns(
      skinProfile.concerns.map((selection) => selection.concern.slug),
    );
    setGoalsText(skinProfile.goals.join(", "));
    setPregnancyStatus(skinProfile.pregnancy_status);
    setClimate(skinProfile.climate);
    setRoutineNotes(skinProfile.routine_notes);
    setSensitivities(intakeQuery.data?.sensitivities ?? []);
  }, [intakeQuery.data]);

  const activeZones = useConcernZones(concerns);

  function addCustomSensitivity() {
    const value = customSensitivity.trim();
    if (!value || sensitivities.includes(value)) {
      return;
    }
    setSensitivities((current) => [...current, value]);
    setCustomSensitivity("");
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: IntakePayload = {
      skin_types: [skinType],
      fitzpatrick_skin_type: fitzpatrickSkinType,
      baseline_sensitivity: baselineSensitivity,
      concerns,
      goals: [],
      goals_text: goalsText,
      pregnancy_status: pregnancyStatus,
      climate,
      routine_notes: routineNotes,
      sensitivities,
    };
    saveMutation.mutate(payload);
  }

  if (meQuery.isLoading || meQuery.isError) {
    return <p className="detail-muted">Loading your session...</p>;
  }

  return (
    <>
      <section className={styles.appHero}>
        <p className="landing-eyebrow">Skin intake</p>
        <h1>Build your first skin profile.</h1>
        <p>
          This mobile-friendly intake creates the context Blueskies will use for
          tracking, product scans, regimen analysis, and future photo signals.
        </p>
      </section>

      <form className={styles.intakeForm} onSubmit={submit}>
        <section
          className={[styles.intakeCard, styles.facialPlaceholder].join(" ")}
        >
          <div>
            <p className="landing-eyebrow">Coming soon</p>
            <h2>Facial analysis plugin</h2>
            <p>
              Photo-based analysis will map tone, texture, breakouts, and
              barrier signals. This will feed into the intake form instead of
              manual entry. For now, your answers below light up the face map.
            </p>
          </div>
          <FaceMap activeZones={activeZones} />
        </section>

        <section className={styles.intakeCard}>
          <h2>Skin basics</h2>
          <fieldset className="choice-group">
            <legend>Skin type</legend>
            <SkinTypeSelector
              className={styles.skinTypeGrid}
              name="skin_type"
              optionClassName={["choice-card", styles.skinTypeTile].join(" ")}
              values={[skinType]}
              onChange={(values) => setSkinType(values[0] ?? "unknown")}
            />
          </fieldset>
          <fieldset className="choice-group">
            <legend>Fitzpatrick skin type</legend>
            <div className={styles.fitzpatrickGrid}>
              {fitzpatrickTypeOptions.map((type) => (
                <label
                  className={[
                    "choice-card",
                    styles.fitzpatrickTile,
                    fitzpatrickTileClasses[type.styleKey],
                  ].join(" ")}
                  key={type.value}
                >
                  <input
                    type="radio"
                    name="fitzpatrick_skin_type"
                    value={type.value}
                    checked={fitzpatrickSkinType === type.value}
                    onChange={() => setFitzpatrickSkinType(type.value)}
                  />
                  <span className={styles.fitzpatrickType}>{type.label}</span>
                  <span className={styles.fitzpatrickInfo}>
                    <span className={styles.fitzpatrickTone}>{type.tone}</span>
                    <span className={styles.fitzpatrickResponse}>
                      {type.response}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          <label className="field">
            <span>Baseline sensitivity: {baselineSensitivity}/10</span>
            <input
              type="range"
              min="0"
              max="10"
              value={baselineSensitivity}
              onChange={(event) =>
                setBaselineSensitivity(Number(event.target.value))
              }
            />
          </label>
        </section>

        <section className={styles.intakeCard}>
          <h2>Skin concerns</h2>
          <label className="field">
            <span>Search concerns</span>
            <input
              type="search"
              value={concernSearch}
              onChange={(event) => setConcernSearch(event.target.value)}
              placeholder="Pimples, flaky, redness, eczema..."
            />
          </label>
          {concernSearchTerm.length >= 2 && (
            <fieldset className={styles.concernSection}>
              <legend>Search results</legend>
              {isConcernSearchPending ? (
                <p className="detail-muted">Searching concerns...</p>
              ) : concernSearchQuery.data?.results.length ? (
                <div className="choice-grid">
                  {concernSearchQuery.data.results.map((concern) => (
                    <label className="choice-card" key={concern.slug}>
                      <input
                        type="checkbox"
                        checked={concerns.includes(concern.slug)}
                        onChange={() =>
                          setConcerns((current) =>
                            toggleValue(current, concern.slug),
                          )
                        }
                      />
                      <span>{concern.consumer_label}</span>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="detail-muted">No concern matches yet.</p>
              )}
            </fieldset>
          )}
          <div className={styles.concernSectionStack}>
            {concernOptionsQuery.isLoading && (
              <p className="detail-muted">Loading common concerns...</p>
            )}
            {concernOptionsQuery.data?.groups.map((section) => (
              <fieldset className={styles.concernSection} key={section.group}>
                <legend>{section.label}</legend>
                <div className="choice-grid">
                  {section.concerns.map((concern) => (
                    <label className="choice-card" key={concern.slug}>
                      <input
                        type="checkbox"
                        checked={concerns.includes(concern.slug)}
                        onChange={() =>
                          setConcerns((current) =>
                            toggleValue(current, concern.slug),
                          )
                        }
                      />
                      <span>{concern.consumer_label}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
          </div>
        </section>

        <section className={styles.intakeCard}>
          <h2>Goals and context</h2>
          <TextField
            className="contact-field"
            onChange={setGoalsText}
            value={goalsText}
          >
            <Label>Goals in your own words</Label>
            <TextArea
              placeholder="Fewer breakouts, calmer redness, stronger barrier..."
              rows={4}
              variant="secondary"
            />
          </TextField>
          <label className="field">
            <span>Pregnancy or nursing context</span>
            <select
              value={pregnancyStatus}
              onChange={(event) => setPregnancyStatus(event.target.value)}
            >
              <option value="not_provided">Prefer not to say</option>
              <option value="not_applicable">Not applicable</option>
              <option value="trying">Trying to conceive</option>
              <option value="pregnant">Pregnant</option>
              <option value="nursing">Nursing</option>
            </select>
          </label>
          <TextField
            className="contact-field"
            onChange={setClimate}
            value={climate}
          >
            <Label>Climate or environment</Label>
            <Input
              placeholder="Humid, dry winter air, city pollution..."
              variant="secondary"
            />
          </TextField>
          <TextField
            className="contact-field"
            onChange={setRoutineNotes}
            value={routineNotes}
          >
            <Label>Routine notes</Label>
            <TextArea
              placeholder="What are you using now? What has helped or irritated your skin?"
              rows={4}
              variant="secondary"
            />
          </TextField>
        </section>

        <section className={styles.intakeCard}>
          <h2>Sensitivities and avoid list</h2>
          <SensitivityOptions
            gridClassName="choice-grid"
            optionClassName="choice-card"
            values={sensitivities}
            onToggle={(item) =>
              setSensitivities((current) => toggleValue(current, item))
            }
          />
          <div className={styles.sensitivityAdd}>
            <input
              type="text"
              value={customSensitivity}
              onChange={(event) => setCustomSensitivity(event.target.value)}
              placeholder="Add a custom sensitivity"
            />
            <Button
              type="button"
              variant="ghost"
              onPress={addCustomSensitivity}
            >
              Add
            </Button>
          </div>
        </section>

        <div className={styles.intakeSubmit}>
          <Button type="submit" isDisabled={saveMutation.isPending}>
            {saveMutation.isPending ? "Saving..." : "Save skin profile"}
          </Button>
          {message && <p className="contact-success">{message}</p>}
          {error && <p className="contact-error">{error}</p>}
        </div>
      </form>
    </>
  );
}

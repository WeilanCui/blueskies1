"use client";

import Link from "next/link";
import { Input, Label, TextArea, TextField } from "@heroui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Button } from "../../components/Button";
import FaceMap from "../experience/FaceMap";
import {
  getIntake,
  getMe,
  logout,
  saveIntake,
  type IntakePayload,
} from "../../lib/appApi";

const skinTypes = [
  ["dry", "Dry"],
  ["oily", "Oily"],
  ["combination", "Combination"],
  ["normal", "Normal"],
  ["sensitive", "Sensitive"],
  ["unknown", "Not sure"],
];

const fitzpatrickTypes = [
  ["not_provided", "Not sure / skip"],
  ["type_i", "Type I"],
  ["type_ii", "Type II"],
  ["type_iii", "Type III"],
  ["type_iv", "Type IV"],
  ["type_v", "Type V"],
  ["type_vi", "Type VI"],
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

const concernZones: Record<string, string[]> = {
  acne: ["forehead", "cheeks", "chin"],
  clogged_pores: ["nose", "chin"],
  blackheads: ["nose", "chin"],
  whiteheads: ["forehead", "chin"],
  redness: ["cheeks", "nose"],
  stinging: ["cheeks"],
  reactive_skin: ["cheeks", "forehead"],
  rosacea_prone: ["cheeks", "nose"],
  dryness: ["cheeks", "lips"],
  dehydration: ["cheeks", "forehead"],
  flaking: ["cheeks", "chin"],
  tightness: ["cheeks"],
  barrier_damage: ["cheeks", "forehead"],
  oiliness: ["forehead", "nose", "chin"],
  enlarged_pores: ["nose", "cheeks"],
  shine: ["forehead", "nose"],
  sebaceous_filaments: ["nose"],
  dark_spots: ["cheeks", "forehead"],
  hyperpigmentation: ["cheeks", "forehead"],
  melasma_prone: ["cheeks", "forehead"],
  post_acne_marks: ["cheeks", "chin"],
  roughness: ["cheeks", "forehead"],
  bumps: ["forehead", "cheeks"],
  uneven_texture: ["cheeks", "forehead"],
  dullness: ["cheeks", "forehead"],
  fine_lines: ["eyes", "forehead"],
  wrinkles: ["eyes", "forehead"],
  loss_of_firmness: ["cheeks", "chin"],
  dark_circles: ["eyes"],
  puffiness: ["eyes"],
  eye_fine_lines: ["eyes"],
};

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

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

export default function IntakePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [skinType, setSkinType] = useState("combination");
  const [fitzpatrickSkinType, setFitzpatrickSkinType] = useState("not_provided");
  const [baselineSensitivity, setBaselineSensitivity] = useState(5);
  const [concerns, setConcerns] = useState<string[]>([]);
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
  const saveMutation = useMutation({
    mutationFn: saveIntake,
    onSuccess: (data) => {
      queryClient.setQueryData(["intake"], data);
      queryClient.invalidateQueries({ queryKey: ["me"] });
      setMessage("Your skin profile is saved.");
      setError(null);
    },
    onError: (saveError) => {
      setError(saveError instanceof Error ? saveError.message : "Could not save intake.");
      setMessage(null);
    },
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

  useEffect(() => {
    const skinProfile = intakeQuery.data?.skin_profile;
    if (!skinProfile) {
      return;
    }
    setSkinType(skinProfile.skin_type);
    setFitzpatrickSkinType(skinProfile.fitzpatrick_skin_type);
    setBaselineSensitivity(skinProfile.baseline_sensitivity ?? 5);
    setConcerns(skinProfile.primary_concerns);
    setGoalsText(skinProfile.goals.join(", "));
    setPregnancyStatus(skinProfile.pregnancy_status);
    setClimate(skinProfile.climate);
    setRoutineNotes(skinProfile.routine_notes);
    setSensitivities(intakeQuery.data?.sensitivities ?? []);
  }, [intakeQuery.data]);

  const activeZones = useMemo(() => {
    const zones = new Set<string>();
    for (const concern of concerns) {
      for (const zone of concernZones[concern] ?? []) {
        zones.add(zone);
      }
    }
    return Array.from(zones);
  }, [concerns]);

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
      skin_type: skinType,
      fitzpatrick_skin_type: fitzpatrickSkinType,
      baseline_sensitivity: baselineSensitivity,
      primary_concerns: concerns,
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
    return (
      <main className="app-shell">
        <p className="detail-muted">Loading your session...</p>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <nav className="topbar app-topbar">
        <Link className="brand" href="/">
          Blueskies
        </Link>
        <Button
          type="button"
          variant="ghost"
          isDisabled={logoutMutation.isPending}
          onPress={() => logoutMutation.mutate()}
        >
          Log out
        </Button>
      </nav>

      <section className="app-hero">
        <p className="landing-eyebrow">Skin intake</p>
        <h1>Build your first skin profile.</h1>
        <p>
          This mobile-friendly intake creates the context Blueskies will use for
          tracking, product scans, regimen analysis, and future photo signals.
        </p>
      </section>

      <form className="intake-form" onSubmit={submit}>
        <section className="intake-card facial-placeholder">
          <div>
            <p className="landing-eyebrow">Coming soon</p>
            <h2>Facial analysis plugin</h2>
            <p>
              Photo-based analysis will help map tone, texture, breakouts, and
              barrier signals. For now, your answers below light up the face map.
            </p>
          </div>
          <FaceMap activeZones={activeZones} />
        </section>

        <section className="intake-card">
          <h2>Skin basics</h2>
          <label className="field">
            <span>Skin type</span>
            <select value={skinType} onChange={(event) => setSkinType(event.target.value)}>
              {skinTypes.map(([value, label]) => (
                <option value={value} key={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Fitzpatrick skin type</span>
            <select
              value={fitzpatrickSkinType}
              onChange={(event) => setFitzpatrickSkinType(event.target.value)}
            >
              {fitzpatrickTypes.map(([value, label]) => (
                <option value={value} key={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Baseline sensitivity: {baselineSensitivity}/10</span>
            <input
              type="range"
              min="0"
              max="10"
              value={baselineSensitivity}
              onChange={(event) => setBaselineSensitivity(Number(event.target.value))}
            />
          </label>
        </section>

        <section className="intake-card">
          <h2>Skin concerns</h2>
          <div className="concern-section-stack">
            {concernSections.map((section) => (
              <fieldset className="concern-section" key={section.title}>
                <legend>{section.title}</legend>
                <div className="choice-grid">
                  {section.items.map(([value, label]) => (
                    <label className="choice-card" key={value}>
                      <input
                        type="checkbox"
                        checked={concerns.includes(value)}
                        onChange={() =>
                          setConcerns((current) => toggleValue(current, value))
                        }
                      />
                      <span>{label}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
          </div>
        </section>

        <section className="intake-card">
          <h2>Goals and context</h2>
          <TextField className="contact-field" onChange={setGoalsText} value={goalsText}>
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
          <TextField className="contact-field" onChange={setClimate} value={climate}>
            <Label>Climate or environment</Label>
            <Input placeholder="Humid, dry winter air, city pollution..." variant="secondary" />
          </TextField>
          <TextField className="contact-field" onChange={setRoutineNotes} value={routineNotes}>
            <Label>Routine notes</Label>
            <TextArea
              placeholder="What are you using now? What has helped or irritated your skin?"
              rows={4}
              variant="secondary"
            />
          </TextField>
        </section>

        <section className="intake-card">
          <h2>Sensitivities and avoid list</h2>
          <div className="choice-grid">
            {sensitivityOptions.map((item) => (
              <label className="choice-card" key={item}>
                <input
                  type="checkbox"
                  checked={sensitivities.includes(item)}
                  onChange={() =>
                    setSensitivities((current) => toggleValue(current, item))
                  }
                />
                <span>{item}</span>
              </label>
            ))}
          </div>
          <div className="sensitivity-add">
            <input
              type="text"
              value={customSensitivity}
              onChange={(event) => setCustomSensitivity(event.target.value)}
              placeholder="Add a custom sensitivity"
            />
            <Button type="button" variant="ghost" onPress={addCustomSensitivity}>
              Add
            </Button>
          </div>
        </section>

        <div className="intake-submit">
          <Button type="submit" isDisabled={saveMutation.isPending}>
            {saveMutation.isPending ? "Saving..." : "Save skin profile"}
          </Button>
          {message && <p className="contact-success">{message}</p>}
          {error && <p className="contact-error">{error}</p>}
        </div>
      </form>
    </main>
  );
}

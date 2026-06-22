import type { IntakePayload, IntakeResponse } from "./appApi";

export type ProfileOption = readonly [value: string, label: string];
export type ConcernOption = {
  value: string;
  label: string;
};

export type ConcernSection = {
  title: string;
  items: ConcernOption[];
};

export type FitzpatrickStyleKey =
  | "notProvided"
  | "typeI"
  | "typeII"
  | "typeIII"
  | "typeIV"
  | "typeV"
  | "typeVI";

export type FitzpatrickOption = {
  value: string;
  label: string;
  tone: string;
  response: string;
  styleKey: FitzpatrickStyleKey;
};

export const skinTypeOptions: ProfileOption[] = [
  ["dry", "Dry"],
  ["oily", "Oily"],
  ["combination", "Combination"],
  ["normal", "Normal"],
  ["sensitive", "Sensitive"],
  ["unknown", "Not sure"],
];

export const skinTypeLabels = Object.fromEntries(skinTypeOptions);

export const fitzpatrickTypeOptions: FitzpatrickOption[] = [
  {
    value: "not_provided",
    label: "Not sure",
    tone: "Skip for now",
    response: "You can update this later.",
    styleKey: "notProvided",
  },
  {
    value: "type_i",
    label: "Type I",
    tone: "Ivory",
    response: "Always freckles, always burns or peels, never tans.",
    styleKey: "typeI",
  },
  {
    value: "type_ii",
    label: "Type II",
    tone: "Pale or fair",
    response: "Usually freckles, often burns or peels, rarely tans.",
    styleKey: "typeII",
  },
  {
    value: "type_iii",
    label: "Type III",
    tone: "Fair to beige",
    response: "Might freckle, burns on occasion, sometimes tans.",
    styleKey: "typeIII",
  },
  {
    value: "type_iv",
    label: "Type IV",
    tone: "Olive or light brown",
    response: "Doesn't really freckle, rarely burns, often tans.",
    styleKey: "typeIV",
  },
  {
    value: "type_v",
    label: "Type V",
    tone: "Dark brown",
    response: "Rarely freckles, almost never burns, always tans.",
    styleKey: "typeV",
  },
  {
    value: "type_vi",
    label: "Type VI",
    tone: "Deep brown",
    response: "Never freckles, never burns, always tans.",
    styleKey: "typeVI",
  },
];

export const primaryConcernSections: ConcernSection[] = [
  {
    title: "Primary Focus",
    items: [
      {
        value: "acne_blemishes",
        label: "Acne blemishes: breakouts, post-acne marks",
      },
      { value: "dehydrated_dryness", label: "Dehydrated / dryness" },
      { value: "enlarged_pores", label: "Enlarged pores" },
      { value: "dark_circles", label: "Dark circles" },
      { value: "sun_damage", label: "Sun damage" },
      {
        value: "uneven_tone_hyperpigmentation_dull_skin",
        label: "Uneven skin tone, hyperpigmentation, dull skin",
      },
      {
        value: "wrinkles_firmness_elasticity",
        label: "Wrinkles / firmness / skin elasticity",
      },
      {
        value: "sensitive_reactive_skin",
        label:
          "Sensitive or reactive skin: redness, reactive skin, sensitivity, damaged skin barrier",
      },
    ],
  },
];

export function concernLabelMap(sections: ConcernSection[]): Record<string, string> {
  return Object.fromEntries(
    sections.flatMap((section) =>
      section.items.map((item) => [item.value, item.label]),
    ),
  );
}

export const primaryConcernLabels = concernLabelMap(primaryConcernSections);

export const concernZones: Record<string, string[]> = {
  acne_blemishes: ["forehead", "cheeks", "chin"],
  breakouts: ["forehead", "cheeks", "chin"],
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
  dehydrated_dryness: ["cheeks", "forehead"],
  oiliness: ["forehead", "nose", "chin"],
  enlarged_pores: ["nose", "cheeks"],
  shine: ["forehead", "nose"],
  sebaceous_filaments: ["nose"],
  dark_spots: ["cheeks", "forehead"],
  hyperpigmentation: ["cheeks", "forehead"],
  melasma_prone: ["cheeks", "forehead"],
  post_acne_marks: ["cheeks", "chin"],
  sun_damage: ["cheeks", "forehead"],
  uneven_tone_hyperpigmentation_dull_skin: ["cheeks", "forehead"],
  uneven_skin_tone: ["cheeks", "forehead"],
  dull_skin: ["cheeks", "forehead"],
  roughness: ["cheeks", "forehead"],
  bumps: ["forehead", "cheeks"],
  uneven_texture: ["cheeks", "forehead"],
  dullness: ["cheeks", "forehead"],
  fine_lines: ["eyes", "forehead"],
  wrinkles: ["eyes", "forehead"],
  loss_of_firmness: ["cheeks", "chin"],
  wrinkles_firmness_elasticity: ["eyes", "forehead", "cheeks", "chin"],
  firmness: ["cheeks", "chin"],
  skin_elasticity: ["cheeks", "chin"],
  dark_circles: ["eyes"],
  puffiness: ["eyes"],
  eye_fine_lines: ["eyes"],
  sensitive_reactive_skin: ["cheeks", "forehead"],
  sensitivity: ["cheeks"],
  damaged_skin_barrier: ["cheeks", "forehead"],
};

export const sensitivityOptions = [
  "Fragrance",
  "Essential oils",
  "Denatured alcohol",
  "Retinoids",
  "AHAs / BHAs",
  "Benzoyl peroxide",
  "Sulfates",
  "Lanolin",
];

export function toggleValue(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

export function cleanList(values: string[]): string[] {
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

export function formatToken(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function getSavedSkinTypes(
  skinProfile: IntakeResponse["skin_profile"] | undefined,
): string[] {
  if (!skinProfile) {
    return [];
  }
  if (skinProfile.skin_types.length > 0) {
    return skinProfile.skin_types;
  }
  return [];
}

export function intakeToPayload(
  intake: IntakeResponse | undefined,
  overrides: Partial<IntakePayload> = {},
): IntakePayload {
  const skinProfile = intake?.skin_profile;
  const skinTypes = getSavedSkinTypes(skinProfile);

  return {
    skin_types: skinTypes.length > 0 ? skinTypes : ["unknown"],
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

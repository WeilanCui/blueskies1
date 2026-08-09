export type AnswerType = "single" | "multi";

export type ProductModuleKey =
  | "cleanser"
  | "moisturizer"
  | "sunscreen"
  | "treatment"
  | "active"
  | "eye"
  | "lip"
  | "other";

export type QuestionnaireOption = {
  id: string;
  label: string;
  baseOrder: number;
  pinned?: "first" | "last";
  triggersSafetyGate?: boolean;
};

export type QuestionnaireQuestion = {
  id: string;
  prompt: string;
  type: AnswerType;
  options: QuestionnaireOption[];
};

export const questionnaireVersion = "skincare_feedback_v1";

export const productTypeOptions: Array<{
  id: ProductModuleKey;
  label: string;
}> = [
  { id: "cleanser", label: "Cleanser" },
  { id: "moisturizer", label: "Moisturizer" },
  { id: "sunscreen", label: "Sunscreen" },
  { id: "treatment", label: "Treatment" },
  { id: "active", label: "Active" },
  { id: "eye", label: "Eye" },
  { id: "lip", label: "Lip" },
  { id: "other", label: "Other" },
];

export const overallQuestion: QuestionnaireQuestion = {
  id: "overall",
  prompt: "How did your skin get along with it?",
  type: "single",
  options: [
    { id: "loved", label: "Loved", baseOrder: 1 },
    { id: "worked", label: "Worked", baseOrder: 2 },
    { id: "neutral", label: "Neutral", baseOrder: 3 },
    { id: "mismatch", label: "Mismatch", baseOrder: 4 },
    {
      id: "reaction",
      label: "Reaction",
      baseOrder: 5,
      triggersSafetyGate: true,
    },
  ],
};

export const goodQuestion: QuestionnaireQuestion = {
  id: "good",
  prompt: "What improved?",
  type: "multi",
  options: [
    { id: "hydration", label: "Hydration", baseOrder: 1 },
    { id: "softness", label: "Softness", baseOrder: 2 },
    { id: "smoothness", label: "Smoothness", baseOrder: 3 },
    { id: "calmness", label: "Calmness", baseOrder: 4 },
    { id: "brightness", label: "Brightness", baseOrder: 5 },
    { id: "clarity", label: "Clarity", baseOrder: 6 },
    { id: "tone", label: "Tone", baseOrder: 7 },
    { id: "texture", label: "Texture", baseOrder: 8 },
    { id: "oiliness", label: "Oiliness", baseOrder: 9 },
    { id: "makeup", label: "Makeup", baseOrder: 10 },
    { id: "other", label: "Other", baseOrder: 99, pinned: "last" },
  ],
};

export const offQuestion: QuestionnaireQuestion = {
  id: "off",
  prompt: "What felt off?",
  type: "multi",
  options: [
    { id: "dryness", label: "Dryness", baseOrder: 1 },
    { id: "tightness", label: "Tightness", baseOrder: 2 },
    { id: "stinging", label: "Stinging", baseOrder: 3 },
    { id: "burning", label: "Burning", baseOrder: 4, triggersSafetyGate: true },
    { id: "itching", label: "Itching", baseOrder: 5 },
    { id: "redness", label: "Redness", baseOrder: 6 },
    { id: "peeling", label: "Peeling", baseOrder: 7 },
    { id: "bumps", label: "Bumps", baseOrder: 8 },
    { id: "breakouts", label: "Breakouts", baseOrder: 9 },
    { id: "clogging", label: "Clogging", baseOrder: 10 },
    { id: "greasiness", label: "Greasiness", baseOrder: 11 },
    { id: "stickiness", label: "Stickiness", baseOrder: 12 },
    { id: "pilling", label: "Pilling", baseOrder: 13 },
    { id: "scent", label: "Scent", baseOrder: 14 },
    { id: "residue", label: "Residue", baseOrder: 15 },
    { id: "eyes", label: "Eyes", baseOrder: 16, triggersSafetyGate: true },
    { id: "other", label: "Other", baseOrder: 99, pinned: "last" },
  ],
};

export const timingQuestion: QuestionnaireQuestion = {
  id: "timing",
  prompt: "When did you notice it?",
  type: "single",
  options: [
    { id: "immediate", label: "Immediate", baseOrder: 1 },
    { id: "today", label: "Today", baseOrder: 2 },
    { id: "tomorrow", label: "Tomorrow", baseOrder: 3 },
    { id: "days", label: "Days", baseOrder: 4 },
    { id: "weeks", label: "Weeks", baseOrder: 5 },
    { id: "sun", label: "Sun", baseOrder: 6 },
  ],
};

export const noticeabilityQuestion: QuestionnaireQuestion = {
  id: "noticeability",
  prompt: "How noticeable was it?",
  type: "single",
  options: [
    { id: "barely", label: "Barely", baseOrder: 1 },
    { id: "mild", label: "Mild", baseOrder: 2 },
    { id: "moderate", label: "Moderate", baseOrder: 3 },
    { id: "strong", label: "Strong", baseOrder: 4 },
    {
      id: "severe",
      label: "Severe",
      baseOrder: 5,
      triggersSafetyGate: true,
    },
  ],
};

export const useAgainQuestion: QuestionnaireQuestion = {
  id: "use_again",
  prompt: "Would you use it again?",
  type: "single",
  options: [
    { id: "yes", label: "Yes", baseOrder: 1 },
    { id: "less", label: "Less", baseOrder: 2 },
    { id: "maybe", label: "Maybe", baseOrder: 3 },
    { id: "no", label: "No", baseOrder: 4 },
    { id: "never", label: "Never", baseOrder: 5, triggersSafetyGate: true },
  ],
};

export const safetyQuestion: QuestionnaireQuestion = {
  id: "safety",
  prompt: "Any of these?",
  type: "multi",
  options: [
    { id: "breathing", label: "Breathing", baseOrder: 1 },
    { id: "swelling", label: "Swelling", baseOrder: 2 },
    { id: "hives", label: "Hives", baseOrder: 3 },
    { id: "blisters", label: "Blisters", baseOrder: 4 },
    { id: "pain", label: "Pain", baseOrder: 5 },
    { id: "infection", label: "Infection", baseOrder: 6 },
    { id: "vision", label: "Vision", baseOrder: 7 },
    { id: "spreading", label: "Spreading", baseOrder: 8 },
  ],
};

export const productModules: Record<ProductModuleKey, QuestionnaireQuestion[]> =
  {
    cleanser: [
      {
        id: "cleanser_result",
        prompt: "How did cleansing go?",
        type: "multi",
        options: [
          { id: "clean", label: "Clean", baseOrder: 1 },
          { id: "comfort", label: "Comfort", baseOrder: 2 },
          { id: "stripped", label: "Stripped", baseOrder: 3 },
          { id: "residue", label: "Residue", baseOrder: 4 },
          { id: "sunscreen", label: "Sunscreen", baseOrder: 5 },
          { id: "makeup", label: "Makeup", baseOrder: 6 },
          { id: "eyes", label: "Eyes", baseOrder: 7, triggersSafetyGate: true },
          { id: "texture", label: "Texture", baseOrder: 8 },
        ],
      },
    ],
    moisturizer: [
      {
        id: "moisturizer_wear",
        prompt: "How did hydration wear?",
        type: "multi",
        options: [
          { id: "hydration", label: "Hydration", baseOrder: 1 },
          { id: "calmness", label: "Calmness", baseOrder: 2 },
          { id: "softness", label: "Softness", baseOrder: 3 },
          { id: "lightweight", label: "Lightweight", baseOrder: 4 },
          { id: "rich", label: "Rich", baseOrder: 5 },
          { id: "greasiness", label: "Greasiness", baseOrder: 6 },
          { id: "stickiness", label: "Stickiness", baseOrder: 7 },
          { id: "clogging", label: "Clogging", baseOrder: 8 },
          { id: "pilling", label: "Pilling", baseOrder: 9 },
        ],
      },
    ],
    sunscreen: [
      {
        id: "sunscreen_cast",
        prompt: "How was the cast?",
        type: "single",
        options: [
          { id: "none", label: "None", baseOrder: 1 },
          { id: "slight", label: "Slight", baseOrder: 2 },
          { id: "noticeable", label: "Noticeable", baseOrder: 3 },
          { id: "strong", label: "Strong", baseOrder: 4 },
        ],
      },
      {
        id: "sunscreen_wear",
        prompt: "How did sunscreen wear?",
        type: "multi",
        options: [
          { id: "matte", label: "Matte", baseOrder: 1 },
          { id: "dewy", label: "Dewy", baseOrder: 2 },
          { id: "greasiness", label: "Greasiness", baseOrder: 3 },
          { id: "stickiness", label: "Stickiness", baseOrder: 4 },
          { id: "eyes", label: "Eyes", baseOrder: 5, triggersSafetyGate: true },
          { id: "pilling", label: "Pilling", baseOrder: 6 },
          { id: "protection", label: "Protection", baseOrder: 7 },
          { id: "redness", label: "Redness", baseOrder: 8 },
        ],
      },
    ],
    treatment: [
      {
        id: "treatment_result",
        prompt: "What changed?",
        type: "multi",
        options: [
          { id: "glow", label: "Glow", baseOrder: 1 },
          { id: "texture", label: "Texture", baseOrder: 2 },
          { id: "calmness", label: "Calmness", baseOrder: 3 },
          { id: "tone", label: "Tone", baseOrder: 4 },
          { id: "clarity", label: "Clarity", baseOrder: 5 },
          { id: "breakouts", label: "Breakouts", baseOrder: 6 },
          { id: "dryness", label: "Dryness", baseOrder: 7 },
          { id: "stinging", label: "Stinging", baseOrder: 8 },
          { id: "peeling", label: "Peeling", baseOrder: 9 },
          { id: "bumps", label: "Bumps", baseOrder: 10 },
        ],
      },
    ],
    active: [
      {
        id: "active_result",
        prompt: "How did treatment go?",
        type: "multi",
        options: [
          { id: "clarity", label: "Clarity", baseOrder: 1 },
          { id: "texture", label: "Texture", baseOrder: 2 },
          { id: "pores", label: "Pores", baseOrder: 3 },
          { id: "breakouts", label: "Breakouts", baseOrder: 4 },
          { id: "dryness", label: "Dryness", baseOrder: 5 },
          { id: "flaking", label: "Flaking", baseOrder: 6 },
          { id: "sensitivity", label: "Sensitivity", baseOrder: 7 },
          { id: "strength", label: "Strength", baseOrder: 8 },
          { id: "consistency", label: "Consistency", baseOrder: 9 },
        ],
      },
    ],
    eye: [
      {
        id: "eye_result",
        prompt: "How did the eye area respond?",
        type: "multi",
        options: [
          { id: "dryness", label: "Dryness", baseOrder: 1 },
          { id: "puffiness", label: "Puffiness", baseOrder: 2 },
          { id: "smoothness", label: "Smoothness", baseOrder: 3 },
          {
            id: "stinging",
            label: "Stinging",
            baseOrder: 4,
            triggersSafetyGate: true,
          },
          {
            id: "watering",
            label: "Watering",
            baseOrder: 5,
            triggersSafetyGate: true,
          },
          { id: "bumps", label: "Bumps", baseOrder: 6 },
          { id: "heaviness", label: "Heaviness", baseOrder: 7 },
          { id: "creasing", label: "Creasing", baseOrder: 8 },
        ],
      },
    ],
    lip: [
      {
        id: "lip_result",
        prompt: "How did lips respond?",
        type: "multi",
        options: [
          { id: "dryness", label: "Dryness", baseOrder: 1 },
          { id: "cracking", label: "Cracking", baseOrder: 2 },
          { id: "comfort", label: "Comfort", baseOrder: 3 },
          { id: "stickiness", label: "Stickiness", baseOrder: 4 },
          { id: "gloss", label: "Gloss", baseOrder: 5 },
          { id: "tingling", label: "Tingling", baseOrder: 6 },
          {
            id: "burning",
            label: "Burning",
            baseOrder: 7,
            triggersSafetyGate: true,
          },
          {
            id: "swelling",
            label: "Swelling",
            baseOrder: 8,
            triggersSafetyGate: true,
          },
          { id: "peeling", label: "Peeling", baseOrder: 9 },
        ],
      },
    ],
    other: [
      {
        id: "other_result",
        prompt: "How did it perform?",
        type: "multi",
        options: [
          { id: "hydration", label: "Hydration", baseOrder: 1 },
          { id: "texture", label: "Texture", baseOrder: 2 },
          { id: "calmness", label: "Calmness", baseOrder: 3 },
          { id: "brightness", label: "Brightness", baseOrder: 4 },
          { id: "greasiness", label: "Greasiness", baseOrder: 5 },
          { id: "stickiness", label: "Stickiness", baseOrder: 6 },
          { id: "scent", label: "Scent", baseOrder: 7 },
          { id: "pilling", label: "Pilling", baseOrder: 8 },
        ],
      },
    ],
  };

export function orderOptions(
  options: QuestionnaireOption[],
  selectionCounts: Record<string, number> = {},
): QuestionnaireOption[] {
  return [...options].sort((a, b) => {
    if (a.pinned === "first" && b.pinned !== "first") {
      return -1;
    }
    if (b.pinned === "first" && a.pinned !== "first") {
      return 1;
    }
    if (a.pinned === "last" && b.pinned !== "last") {
      return 1;
    }
    if (b.pinned === "last" && a.pinned !== "last") {
      return -1;
    }

    const countDelta =
      (selectionCounts[b.id] ?? 0) - (selectionCounts[a.id] ?? 0);
    return countDelta || a.baseOrder - b.baseOrder;
  });
}

export function inferProductModule(
  category: string | undefined,
  name = "",
): ProductModuleKey {
  const text = `${category ?? ""} ${name}`.toLowerCase();
  if (
    text.includes("cleanser") ||
    text.includes("cleanse") ||
    text.includes("wash")
  ) {
    return "cleanser";
  }
  if (
    text.includes("sunscreen") ||
    text.includes("spf") ||
    text.includes("sunblock")
  ) {
    return "sunscreen";
  }
  if (text.includes("eye")) {
    return "eye";
  }
  if (text.includes("lip")) {
    return "lip";
  }
  if (
    text.includes("moistur") ||
    text.includes("cream") ||
    text.includes("lotion") ||
    text.includes("balm")
  ) {
    return "moisturizer";
  }
  if (
    text.includes("retinol") ||
    text.includes("retinoid") ||
    text.includes("exfol") ||
    text.includes("acid") ||
    text.includes("acne") ||
    text.includes("benzoyl")
  ) {
    return "active";
  }
  if (
    text.includes("serum") ||
    text.includes("essence") ||
    text.includes("toner") ||
    text.includes("treatment")
  ) {
    return "treatment";
  }
  return "other";
}

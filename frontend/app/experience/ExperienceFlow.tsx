"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Button } from "../../components/Button";
import { Panel } from "../../components/Panel";
import { UploadButton } from "../../components/UploadButton";
import FaceMap from "./FaceMap";

type Step =
  | "scan"
  | "intake"
  | "analysis"
  | "sensitivities"
  | "products"
  | "recommendations";

type CurrentProduct = {
  id: string;
  name: string;
  ingredients: string;
};

type Recommendation = {
  name: string;
  brand: string;
  category: string;
  match: number;
  rationale: string;
  actives: string[];
  avoids: string[];
  concerns: string[];
};

const STEPS: { id: Step; label: string }[] = [
  { id: "scan", label: "Facial scan" },
  { id: "intake", label: "Skin intake" },
  { id: "analysis", label: "Target areas" },
  { id: "sensitivities", label: "Sensitivities" },
  { id: "products", label: "Your products" },
  { id: "recommendations", label: "Recommendations" },
];

const CONCERNS = [
  { id: "acne", label: "Acne & breakouts", zones: ["forehead", "chin", "cheeks"] },
  { id: "redness", label: "Redness & sensitivity", zones: ["cheeks", "nose"] },
  { id: "dryness", label: "Dryness & dehydration", zones: ["cheeks", "lips"] },
  { id: "oiliness", label: "Oiliness & pores", zones: ["forehead", "nose", "chin"] },
  { id: "pigmentation", label: "Dark spots", zones: ["cheeks", "forehead"] },
  { id: "aging", label: "Fine lines", zones: ["eyes", "forehead"] },
  { id: "dark_circles", label: "Dark circles", zones: ["eyes"] },
];

const SENSITIVITY_PRESETS = [
  "Fragrance",
  "Essential oils",
  "Denatured alcohol",
  "Retinoids",
  "AHAs / BHAs",
  "Silicones",
  "Sulfates",
  "Parabens",
  "Nickel",
];

const CONCERN_TO_ZONES = CONCERNS.reduce<Record<string, string[]>>((acc, concern) => {
  acc[concern.id] = concern.zones;
  return acc;
}, {});

const SAMPLE_PRODUCTS: CurrentProduct[] = [
  {
    id: "sample-1",
    name: "Gentle Hydrating Cleanser",
    ingredients:
      "Water, Glycerin, Cetearyl Alcohol, Ceramide NP, Hyaluronic Acid, Phenoxyethanol",
  },
  {
    id: "sample-2",
    name: "Daily Barrier Moisturizer",
    ingredients:
      "Water, Squalane, Niacinamide, Panthenol, Ceramide AP, Cholesterol, Tocopherol",
  },
];

const SAMPLE_RECOMMENDATIONS: Recommendation[] = [
  {
    name: "Hydrating Facial Cleanser",
    brand: "CeraVe",
    category: "Cleanser",
    match: 93,
    rationale:
      "Non-foaming wash that cleanses without stripping — a safe daily base for most skin types.",
    actives: ["Ceramides", "Hyaluronic Acid", "Glycerin"],
    avoids: ["Fragrance", "Essential oils"],
    concerns: ["dryness", "redness"],
  },
  {
    name: "Niacinamide 10% + Zinc 1%",
    brand: "The Ordinary",
    category: "Treatment serum",
    match: 91,
    rationale:
      "Helps balance oil, calm visible redness, and refine the look of pores on the T-zone.",
    actives: ["Niacinamide", "Zinc PCA"],
    avoids: ["Fragrance", "Essential oils"],
    concerns: ["oiliness", "acne", "redness"],
  },
  {
    name: "Ultra Facial Cream",
    brand: "Kiehl's",
    category: "Moisturizer",
    match: 90,
    rationale:
      "Lightweight hydration for cheeks and barrier support without a heavy finish.",
    actives: ["Squalane", "Glycerin", "Glacial Glycoprotein"],
    avoids: ["Fragrance", "Denatured alcohol"],
    concerns: ["dryness", "aging"],
  },
  {
    name: "Discoloration Correcting Serum",
    brand: "Good Molecules",
    category: "Treatment serum",
    match: 88,
    rationale:
      "Targets uneven tone on cheeks and forehead with a gentle brightening approach.",
    actives: ["Tranexamic Acid", "Niacinamide"],
    avoids: ["Retinoids", "AHAs / BHAs", "Fragrance"],
    concerns: ["pigmentation", "aging", "dark_circles"],
  },
  {
    name: "Salicylic Acid 2% Solution",
    brand: "Paula's Choice",
    category: "Exfoliant",
    match: 87,
    rationale:
      "Clears congestion on forehead, nose, and chin while keeping pores looking refined.",
    actives: ["Salicylic Acid", "Green Tea Extract"],
    avoids: ["AHAs / BHAs", "Fragrance", "Essential oils"],
    concerns: ["acne", "oiliness"],
  },
  {
    name: "Caffeine Solution 5% + EGCG",
    brand: "The Ordinary",
    category: "Eye treatment",
    match: 86,
    rationale:
      "Reduces the look of under-eye puffiness and shadowing mapped around the eye zone.",
    actives: ["Caffeine", "EGCG"],
    avoids: ["Fragrance", "Essential oils", "Denatured alcohol"],
    concerns: ["dark_circles", "aging"],
  },
  {
    name: "UV Clear SPF 46",
    brand: "EltaMD",
    category: "Sunscreen",
    match: 95,
    rationale:
      "Daily SPF that fits most routines and helps prevent further tone unevenness.",
    actives: ["Niacinamide", "Zinc Oxide", "Octinoxate"],
    avoids: ["Fragrance", "Essential oils"],
    concerns: ["pigmentation", "aging", "redness", "acne"],
  },
];

function relevantAvoids(
  product: Recommendation,
  sensitivities: string[],
): string[] {
  return sensitivities.filter((item) => product.avoids.includes(item));
}

function buildRecommendations(
  concerns: string[],
  sensitivities: string[],
): Recommendation[] {
  const selectedConcerns =
    concerns.length > 0 ? concerns : ["dryness", "oiliness", "pigmentation"];

  const ranked = SAMPLE_RECOMMENDATIONS.map((product) => {
    const overlap = product.concerns.filter((concern) =>
      selectedConcerns.includes(concern),
    ).length;
    const conflictCount = relevantAvoids(product, sensitivities).length;

    return {
      ...product,
      match: Math.max(
        72,
        product.match + overlap * 3 - conflictCount * 8,
      ),
      avoids: relevantAvoids(product, sensitivities),
      relevance: overlap,
    };
  })
    .sort((a, b) => b.match - a.match || b.relevance - a.relevance)
    .slice(0, 5);

  return ranked;
}

export default function ExperienceFlow() {
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [skinType, setSkinType] = useState("combination");
  const [concerns, setConcerns] = useState<string[]>([]);
  const [goals, setGoals] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [sensitivities, setSensitivities] = useState<string[]>([]);
  const [customSensitivity, setCustomSensitivity] = useState("");
  const [products, setProducts] = useState<CurrentProduct[]>(SAMPLE_PRODUCTS);
  const [researchStatus, setResearchStatus] = useState<string | null>(null);
  const [researching, setResearching] = useState(false);

  const activeZones = useMemo(() => {
    const zones = new Set<string>();
    for (const concern of concerns) {
      for (const zone of CONCERN_TO_ZONES[concern] ?? []) {
        zones.add(zone);
      }
    }
    return Array.from(zones);
  }, [concerns]);

  const recommendations = useMemo(
    () => buildRecommendations(concerns, sensitivities),
    [concerns, sensitivities],
  );



  function toggleConcern(id: string) {
    setConcerns((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  }

  function toggleSensitivity(value: string) {
    setSensitivities((current) =>
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    );
  }

  function addCustomSensitivity() {
    const value = customSensitivity.trim();
    if (!value || sensitivities.includes(value)) return;
    setSensitivities((current) => [...current, value]);
    setCustomSensitivity("");
  }

  function updateProduct(id: string, field: "name" | "ingredients", value: string) {
    setProducts((current) =>
      current.map((product) =>
        product.id === id ? { ...product, [field]: value } : product,
      ),
    );
  }

  function addProduct() {
    setProducts((current) => [
      ...current,
      { id: String(Date.now()), name: "", ingredients: "" },
    ]);
  }

  function removeProduct(id: string) {
    setProducts((current) =>
      current.length === 1 ? current : current.filter((product) => product.id !== id),
    );
  }

  async function runIngredientResearch() {
    const validProducts = products.filter(
      (product) => product.name.trim() && product.ingredients.trim(),
    );
    if (validProducts.length === 0) {
      setResearchStatus("Add at least one product with an INCI ingredient list.");
      return;
    }

    setResearching(true);
    setResearchStatus("Researching ingredients across your routine…");

    try {
      for (const product of validProducts) {
        const response = await fetch("/api/formulations/submit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: product.name,
            brand: "Current routine",
            formulation: product.ingredients,
          }),
        });

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail ?? `Failed to research ${product.name}`);
        }
      }

      setResearchStatus(
        `Researched ${validProducts.length} product${validProducts.length === 1 ? "" : "s"}. Ingredient profiles are ready in Compounds.`,
      );
    } catch (error) {
      setResearchStatus(
        error instanceof Error ? error.message : "Ingredient research failed.",
      );
    } finally {
      setResearching(false);
    }
  }

  async function runAnalysis() {
    setAnalyzing(true);
    await new Promise((resolve) => setTimeout(resolve, 1400));
    setAnalyzing(false);
  }

  return (
    <div className="experience-flow">
      <ol className="experience-steps" aria-label="Progress">
        {STEPS.map((item, index) => (
          <li
            key={item.id}
          >
            <span className="experience-step-index">{index + 1}</span>
            <span>{item.label}</span>
          </li>
        ))}
      </ol>

      <Panel split>
        <div className="experience-copy">
          <h2>Facial analysis</h2>
          <p className="lede">
            Upload a clear, front-facing photo. Blueskies maps texture, tone,
            and congestion patterns to guide your routine.
          </p>
          <UploadButton
            onFileSelect={(file) => setPhotoPreview(URL.createObjectURL(file))}
          >
            {photoPreview ? "Replace photo" : "Upload facial photo"}
          </UploadButton>
          {photoPreview ? (
            <img src={photoPreview} alt="Uploaded facial preview" className="photo-preview" />
          ) : (
            <p className="field-hint">
              Photo is optional in this demo — you can continue and map target
              areas from your intake answers.
            </p>
          )}
        </div>
        <FaceMap activeZones={activeZones} analyzing={analyzing} />

      </Panel>

      <Panel>
        <div className="experience-copy">
          <h2>Skincare intake</h2>
          <p className="lede">
            Tell us about your skin so we can prioritize the right target areas.
          </p>
        </div>

        <div className="intake-grid">
          <label className="field">
            <span>Skin type</span>
            <select value={skinType} onChange={(event) => setSkinType(event.target.value)}>
              <option value="dry">Dry</option>
              <option value="oily">Oily</option>
              <option value="combination">Combination</option>
              <option value="normal">Normal</option>
              <option value="sensitive">Sensitive</option>
            </select>
          </label>

          <fieldset className="choice-group">
            <legend>Primary Focus</legend>
            <div className="choice-grid">
              {CONCERNS.map((concern) => (
                <label className="choice-card" key={concern.id}>
                  <input
                    type="checkbox"
                    checked={concerns.includes(concern.id)}
                    onChange={() => toggleConcern(concern.id)}
                  />
                  <span>{concern.label}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <label className="field">
            <span>Goals in your own words</span>
            <textarea
              rows={4}
              value={goals}
              onChange={(event) => setGoals(event.target.value)}
              placeholder="Even tone, fewer breakouts, stronger barrier…"
            />
          </label>
        </div>

        <div className="experience-actions">

          <button
            className="primary-button"
            type="button"
            disabled={concerns.length === 0}
            onClick={runAnalysis}
          >
            Analyze my skin
          </button>
        </div>
      </Panel>

      <Panel split>
        <div className="experience-copy">
          <h2>Target areas recognized</h2>
          <p className="lede">
            Based on your scan and intake, these facial zones need the most
            attention in your routine.
          </p>
          <ul className="analysis-summary">
            <li>
              <strong>Skin type:</strong> {skinType}
            </li>
            <li>
              <strong>Priority zones:</strong> {activeZones.length} mapped
            </li>
            <li>
              <strong>Concerns:</strong>{" "}
              {concerns
                .map((id) => CONCERNS.find((item) => item.id === id)?.label)
                .filter(Boolean)
                .join(", ")}
            </li>
          </ul>
        </div>
        <FaceMap activeZones={activeZones} />
        <div className="experience-actions">
        </div>
      </Panel>

      <Panel>
        <div className="experience-copy">
          <h2>Sensitivities & avoid list</h2>
          <p className="lede">
            Flag ingredients or categories you want excluded from recommendations.
          </p>
        </div>

        <div className="choice-grid">
          {SENSITIVITY_PRESETS.map((item) => (
            <label className="choice-card" key={item}>
              <input
                type="checkbox"
                checked={sensitivities.includes(item)}
                onChange={() => toggleSensitivity(item)}
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
          <button className="ghost-button" type="button" onClick={addCustomSensitivity}>
            Add
          </button>
        </div>

        {sensitivities.length > 0 && (
          <div className="chip-row">
            {sensitivities.map((item) => (
              <button
                key={item}
                type="button"
                className="chip chip-button"
                onClick={() => toggleSensitivity(item)}
              >
                {item} ×
              </button>
            ))}
          </div>
        )}
      </Panel>

      <Panel>
        <div className="experience-copy">
          <h2>Your current products</h2>
          <p className="lede">
            Sample products are pre-filled for this demo. Edit them or add your
            own INCI lists — ingredient research is optional while the backend
            integration is in progress.
          </p>
        </div>

        <div className="product-stack">
          {products.map((product) => (
            <article className="product-card" key={product.id}>
              <div className="product-card-head">
                <strong>Product</strong>
                {products.length > 1 && (
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={() => removeProduct(product.id)}
                  >
                    Remove
                  </button>
                )}
              </div>
              <label className="field">
                <span>Product name</span>
                <input
                  type="text"
                  value={product.name}
                  onChange={(event) =>
                    updateProduct(product.id, "name", event.target.value)
                  }
                  placeholder="Hydrating Cleanser"
                />
              </label>
              <label className="field">
                <span>INCI ingredient list</span>
                <textarea
                  rows={5}
                  value={product.ingredients}
                  onChange={(event) =>
                    updateProduct(product.id, "ingredients", event.target.value)
                  }
                  placeholder="Water, Glycerin, Niacinamide, Phenoxyethanol"
                />
              </label>
            </article>
          ))}
        </div>

        <button className="ghost-button" type="button" onClick={addProduct}>
          + Add another product
        </button>

        {researchStatus && <p className="detail-muted">{researchStatus}</p>}

        <div className="experience-actions">

          <button
            className="ghost-button"
            type="button"
            disabled={researching}
            onClick={runIngredientResearch}
          >
            {researching ? "Researching…" : "Research ingredients"}
          </button>
          <button className="primary-button" type="button" onClick={() => { }}>
            See recommendations
          </button>
        </div>
      </Panel>

      <Panel>
        <div className="experience-copy">
          <h2>Recommended routine</h2>
          <p className="lede">
            Sample recommendations ranked for your concerns and sensitivities.
            Live product matching will replace these once the catalog is connected.
          </p>
          <p className="demo-note">Demo data — not a live purchase or medical recommendation.</p>
        </div>

        <div className="recommendation-grid">
          {recommendations.map((item) => (
            <article className="recommendation-card" key={`${item.brand}-${item.name}`}>
              <div className="recommendation-head">
                <div>
                  <span className="tag">{item.category}</span>
                  <p className="recommendation-brand">{item.brand}</p>
                  <h3>{item.name}</h3>
                </div>
                <span className="match-score">{item.match}% match</span>
              </div>
              <p>{item.rationale}</p>
              <div className="chip-row">
                {item.actives.map((active) => (
                  <span className="chip" key={active}>
                    {active}
                  </span>
                ))}
              </div>
              {item.avoids.length > 0 && (
                <p className="recommendation-avoid">
                  Avoids your flags: {item.avoids.join(", ")}
                </p>
              )}
            </article>
          ))}
        </div>

        <div className="experience-actions">

          <Link className="primary-button link-button" href="/compounds">
            Review ingredient research
          </Link>
        </div>
      </Panel>

    </div >
  );
}

"use client";

import Link from "next/link";
import { useState } from "react";
import { Panel } from "../components/Panel";

type IngredientResult = {
  name: string;
  position: number;
  compound_id: number | null;
  parse_status: string;
  inci_properties: number;
  pubchem_descriptors: number;
  articles_linked: number;
  errors: string[];
};

type SubmitResponse = {
  formulation: {
    id: number;
    name: string;
    brand: string;
    enrichment_status: string;
    ingredient_count: number;
  };
  ingestion: {
    ingredient_count: number;
    enrichment_status: string;
    ingredients: IngredientResult[];
  };
};

function formatLabel(value: string): string {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export default function ProductSubmitForm() {
  const [name, setName] = useState("");
  const [brand, setBrand] = useState("");
  const [formulation, setFormulation] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SubmitResponse | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch("/api/formulations/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, brand, formulation }),
      });

      const data = await response.json();
      if (!response.ok) {
        setError(data.detail ?? "Submission failed.");
        return;
      }

      setResult(data as SubmitResponse);
    } catch {
      setError("Could not reach the backend API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="submit-layout">
      <Panel as="form" variant="form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Product name</span>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Hydrating Daily Serum"
            required
          />
        </label>

        <label className="field">
          <span>Brand (optional)</span>
          <input
            type="text"
            value={brand}
            onChange={(event) => setBrand(event.target.value)}
            placeholder="Blueskies Labs"
          />
        </label>

        <label className="field">
          <span>INCI formulation</span>
          <textarea
            value={formulation}
            onChange={(event) => setFormulation(event.target.value)}
            placeholder={"Water, Glycerin, Niacinamide, Phenoxyethanol"}
            rows={8}
            required
          />
          <span className="field-hint">
            Paste a comma- or line-separated INCI list. Each ingredient will be
            parsed, ingested from INCI + PubChem/PubMed, and stored as a
            compound.
          </span>
        </label>

        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? "Ingesting ingredients…" : "Submit product"}
        </button>
      </Panel>

      {error && (
        <Panel as="div" variant="notice" error>
          {error}
        </Panel>
      )}

      {result && (
        <Panel variant="results">
          <div className="results-header">
            <div>
              <h2>{result.formulation.name}</h2>
              {result.formulation.brand && (
                <p className="detail-muted">{result.formulation.brand}</p>
              )}
            </div>
            <span className={`badge badge-${result.formulation.enrichment_status}`}>
              {formatLabel(result.formulation.enrichment_status)}
            </span>
          </div>

          <p className="detail-muted">
            {result.ingestion.ingredient_count} ingredients processed.{" "}
            <Link href="/compounds">Browse all compounds &rarr;</Link>
          </p>

          <ul className="ingest-results">
            {result.ingestion.ingredients.map((ingredient) => (
              <li className="ingest-row" key={`${ingredient.position}-${ingredient.name}`}>
                <div className="ingest-main">
                  <strong>
                    {ingredient.position}. {ingredient.name}
                  </strong>
                  <span className="tag">{formatLabel(ingredient.parse_status)}</span>
                </div>
                <div className="ingest-meta">
                  <span>{ingredient.inci_properties} INCI properties</span>
                  <span>{ingredient.pubchem_descriptors} PubChem descriptors</span>
                  <span>{ingredient.articles_linked} articles</span>
                  {ingredient.compound_id && (
                    <Link href="/compounds">Compound #{ingredient.compound_id}</Link>
                  )}
                </div>
                {ingredient.errors.length > 0 && (
                  <p className="ingest-errors">{ingredient.errors.join(" · ")}</p>
                )}
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}

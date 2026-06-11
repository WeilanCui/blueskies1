"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import styles from "./compounds.module.css";

export type CompoundStructure = {
  smiles: string;
  inchi: string;
  inchikey: string;
  molecular_formula: string;
  molecular_weight: number | null;
  match_quality: string;
  source: string;
};

export type CompoundAlias = {
  alias_text: string;
  alias_type: string;
  source: string;
};

export type CompoundIdentifier = {
  id_type: string;
  id_value: string;
  source: string;
  is_primary: boolean;
};

export type CompoundProperty = {
  key: string;
  label: string;
  value: string;
  inherited_from: string;
  source_type: string;
  confidence: number;
  evidence_summary: string;
};

export type ChemicalClassMembership = {
  chemical_class: {
    id: number;
    name: string;
    slug: string;
    description: string;
    parent: number | null;
  };
  is_primary: boolean;
  is_active: boolean;
  confidence: number;
  source_type: string;
  source_ref: string;
  rationale: string;
};

export type Compound = {
  id: number;
  canonical_inci: string;
  display_name: string;
  entity_type: string;
  primary_cas: string;
  structure_resolvable: boolean;
  enrichment_status: string;
  notes: string;
  structure: CompoundStructure | null;
  aliases: CompoundAlias[];
  identifiers: CompoundIdentifier[];
  chemical_classes: ChemicalClassMembership[];
  properties: CompoundProperty[];
  inherited_properties: CompoundProperty[];
  effective_properties: CompoundProperty[];
  literature_count: number;
};

function formatLabel(value: string): string {
  if (!value) return "";
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function normalizeCompound(compound: Compound): Compound {
  return {
    ...compound,
    aliases: compound.aliases ?? [],
    identifiers: compound.identifiers ?? [],
    chemical_classes: compound.chemical_classes ?? [],
    properties: compound.properties ?? [],
    inherited_properties: compound.inherited_properties ?? [],
    effective_properties: compound.effective_properties ?? [],
    literature_count: compound.literature_count ?? 0,
  };
}

function CompoundDetail({ compound }: { compound: Compound }) {
  const normalized = normalizeCompound(compound);
  const { structure, identifiers, aliases, chemical_classes } = normalized;
  const properties =
    normalized.effective_properties.length > 0
      ? normalized.effective_properties
      : normalized.properties;
  const hasStructure =
    structure &&
    (structure.molecular_formula ||
      structure.molecular_weight !== null ||
      structure.inchikey ||
      structure.smiles);

  return (
    <div className={styles.compoundDetail}>
      {normalized.notes && <p className={styles.detailNotes}>{normalized.notes}</p>}

      {identifiers.length > 0 && (
        <section className={styles.detailSection}>
          <h3>Identifiers</h3>
          <dl className={styles.kvGrid}>
            {identifiers.map((id) => (
              <div className={styles.kvRow} key={`${id.id_type}-${id.id_value}`}>
                <dt>
                  {id.id_type}
                  {id.is_primary ? " (primary)" : ""}
                </dt>
                <dd>{id.id_value}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {hasStructure && (
        <section className={styles.detailSection}>
          <h3>Structure</h3>
          <dl className={styles.kvGrid}>
            {structure?.molecular_formula && (
              <div className={styles.kvRow}>
                <dt>Formula</dt>
                <dd>{structure.molecular_formula}</dd>
              </div>
            )}
            {structure?.molecular_weight !== null &&
              structure?.molecular_weight !== undefined && (
                <div className={styles.kvRow}>
                  <dt>Mol. weight</dt>
                  <dd>{structure.molecular_weight}</dd>
                </div>
              )}
            {structure?.inchikey && (
                <div className={styles.kvRow}>
                <dt>InChIKey</dt>
                <dd className={styles.mono}>{structure.inchikey}</dd>
              </div>
            )}
            {structure?.smiles && (
              <div className={styles.kvRow}>
                <dt>SMILES</dt>
                <dd className={styles.mono}>{structure.smiles}</dd>
              </div>
            )}
          </dl>
        </section>
      )}

      {aliases.length > 0 && (
        <section className={styles.detailSection}>
          <h3>Aliases</h3>
          <div className="chip-row">
            {aliases.map((alias) => (
              <span className="chip" key={`${alias.alias_type}-${alias.alias_text}`}>
                {alias.alias_text}
                <span className="chip-meta">{alias.alias_type}</span>
              </span>
            ))}
          </div>
        </section>
      )}

      {chemical_classes.length > 0 && (
        <section className={styles.detailSection}>
          <h3>Chemical Classes</h3>
          <div className="chip-row">
            {chemical_classes.map((membership) => (
              <span
                className="chip"
                key={
                  membership.chemical_class?.slug ??
                  `${membership.chemical_class?.name ?? "class"}-${membership.is_primary}`
                }
              >
                {membership.chemical_class?.name ?? "Unknown class"}
                {membership.is_primary && <span className="chip-meta">primary</span>}
              </span>
            ))}
          </div>
        </section>
      )}

      {properties.length > 0 && (
        <section className={styles.detailSection}>
          <h3>Properties</h3>
          <dl className={styles.kvGrid}>
            {properties.map((prop) => (
              <div className={styles.kvRow} key={prop.key}>
                <dt>{prop.label || formatLabel(prop.key)}</dt>
                <dd>
                  {prop.value}
                  <span className={styles.kvSource}>
                    {prop.inherited_from
                      ? `inherited from ${prop.inherited_from}`
                      : prop.source_type}
                  </span>
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <section className={styles.detailSection}>
        <h3>Literature</h3>
        <p className="detail-muted">
          {normalized.literature_count} linked reference
          {normalized.literature_count === 1 ? "" : "s"}
        </p>
      </section>
    </div>
  );
}

export default function CompoundList({ compounds }: { compounds: Compound[] }) {
  const searchParams = useSearchParams();
  const normalizedCompounds = useMemo(
    () => compounds.map(normalizeCompound),
    [compounds],
  );
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    const requestedId = Number(searchParams.get("compound"));
    if (!Number.isFinite(requestedId)) return;

    const match = normalizedCompounds.find((compound) => compound.id === requestedId);
    if (match) {
      setExpandedId(match.id);
      document
        .getElementById(`compound-${match.id}`)
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [normalizedCompounds, searchParams]);

  return (
    <ul className={styles.compoundList}>
      {normalizedCompounds.map((compound) => {
        const isExpanded = expandedId === compound.id;
        const title = compound.display_name || compound.canonical_inci;

        return (
          <li className={styles.compoundItem} id={`compound-${compound.id}`} key={compound.id}>
            <button
              type="button"
              className={styles.compoundRow}
              aria-expanded={isExpanded}
              onClick={() =>
                setExpandedId((current) => (current === compound.id ? null : compound.id))
              }
            >
              <span
                className={
                  isExpanded
                    ? [styles.chevron, styles.chevronOpen].join(" ")
                    : styles.chevron
                }
                aria-hidden
              >
                ▶
              </span>
              <span className={styles.compoundName}>
                <strong>{title}</strong>
                {compound.display_name &&
                  compound.display_name !== compound.canonical_inci && (
                    <span className={styles.compoundSub}>{compound.canonical_inci}</span>
                  )}
              </span>
              <span className={styles.compoundTags}>
                <span className="tag">{formatLabel(compound.entity_type)}</span>
                <span className={`badge badge-${compound.enrichment_status}`}>
                  {formatLabel(compound.enrichment_status)}
                </span>
              </span>
            </button>

            {isExpanded && <CompoundDetail compound={compound} />}
          </li>
        );
      })}
    </ul>
  );
}

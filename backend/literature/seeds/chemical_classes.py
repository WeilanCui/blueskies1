"""Chemical class seed data for inherited compound properties."""

CHEMICAL_CLASSES = [
    {
        "name": "Retinoids",
        "slug": "retinoids",
        "description": (
            "Vitamin A derivatives used as cosmetic actives. Members share "
            "family-level stability and tolerability constraints, while each "
            "compound can override potency, delivery, and use-level details."
        ),
        "assertions": [
            {
                "property_key": "functional_class",
                "value_json": ["active"],
                "source_type": "seed",
                "confidence": 0.95,
                "evidence_summary": "Retinoids are used as active ingredients in topical skincare.",
            },
            {
                "property_key": "efficacy_domain",
                "value_json": ["anti_aging", "anti_acne"],
                "source_type": "seed",
                "confidence": 0.85,
            },
            {
                "property_key": "oxidation_sensitive",
                "value_bool": True,
                "source_type": "seed",
                "confidence": 0.95,
            },
            {
                "property_key": "light_sensitive",
                "value_bool": True,
                "source_type": "seed",
                "confidence": 0.95,
            },
            {
                "property_key": "heat_sensitive",
                "value_bool": True,
                "source_type": "seed",
                "confidence": 0.9,
            },
            {
                "property_key": "irritation_potential",
                "value_text": "moderate",
                "source_type": "seed",
                "confidence": 0.8,
            },
            {
                "property_key": "incompatible_with",
                "value_json": ["strong_oxidizer", "high_ph", "direct_sunlight"],
                "source_type": "seed",
                "confidence": 0.8,
            },
        ],
        "members": [
            {
                "canonical_inci": "RETINOL",
                "display_name": "Retinol",
                "is_primary": True,
                "confidence": 0.99,
                "rationale": "Retinol is a vitamin A derivative and canonical cosmetic retinoid.",
            },
            {
                "canonical_inci": "RETINAL",
                "display_name": "Retinal",
                "is_primary": True,
                "confidence": 0.95,
                "rationale": "Retinaldehyde is a vitamin A derivative in the retinoid family.",
            },
            {
                "canonical_inci": "RETINYL PALMITATE",
                "display_name": "Retinyl Palmitate",
                "is_primary": True,
                "confidence": 0.95,
                "rationale": "Retinyl palmitate is a retinyl ester and retinoid precursor.",
            },
        ],
    },
]

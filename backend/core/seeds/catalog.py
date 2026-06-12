"""Reference catalog seed data aligned with core Brand, Product, and Formulation models."""

REFERENCE_BRANDS = [
    {
        "key": "kiehls",
        "name": "Kiehl's",
        "display_name": "Kiehl's",
        "website_url": "https://www.kiehls.com",
    },
    {
        "key": "paulas-choice",
        "name": "Paula's Choice",
        "display_name": "Paula's Choice",
        "website_url": "https://www.paulaschoice.com",
    },
    {
        "key": "eltamd",
        "name": "EltaMD",
        "display_name": "EltaMD",
        "website_url": "https://www.eltamd.com",
    },
    {
        "key": "cerave",
        "name": "CeraVe",
        "display_name": "CeraVe",
        "website_url": "https://www.cerave.com",
    },
    {
        "key": "the-ordinary",
        "name": "The Ordinary",
        "display_name": "The Ordinary",
        "website_url": "https://theordinary.com",
    },
    {
        "key": "pixi",
        "name": "Pixi",
        "display_name": "Pixi",
        "website_url": "https://www.pixibeauty.com",
    },
]

REFERENCE_PRODUCTS = [
    {
        "key": "ultra-facial-cream",
        "brand_key": "kiehls",
        "name": "Ultra Facial Cream",
        "display_name": "Kiehl's Ultra Facial Cream",
        "category": "Moisturizer",
        "description": (
            "A lightweight, intensely moisturizing daily cream with glacier "
            "glycoprotein extract that helps skin retain moisture all day."
        ),
        "formulations": [
            {
                "key": "us-default",
                "market": "US",
                "version_label": "Current",
                "barcode": "900000000001",
                "raw_inci_text": (
                    "Aqua, Glycerin, Squalane, Niacinamide, Dimethicone, "
                    "Carbomer, Phenoxyethanol"
                ),
                "ingredients": [
                    {"raw_text": "Aqua", "compound_inci": "AQUA"},
                    {
                        "raw_text": "Glycerin",
                        "compound_inci": "GLYCERIN",
                        "active_note": "Draws moisture into the skin, keeping it hydrated.",
                    },
                    {"raw_text": "Squalane"},
                    {
                        "raw_text": "Niacinamide",
                        "compound_inci": "NIACINAMIDE",
                        "is_key_active": True,
                    },
                    {"raw_text": "Dimethicone", "compound_inci": "DIMETHICONE"},
                    {"raw_text": "Carbomer", "compound_inci": "CARBOMER"},
                    {"raw_text": "Phenoxyethanol", "compound_inci": "PHENOXYETHANOL"},
                ],
            }
        ],
    },
    {
        "key": "vitamin-c-serum",
        "brand_key": "paulas-choice",
        "name": "Vitamin C Serum 15%",
        "display_name": "Paula's Choice Vitamin C Serum 15%",
        "category": "Serum",
        "description": (
            "A concentrated antioxidant serum designed to support brighter-looking "
            "skin and improve the look of uneven tone."
        ),
        "formulations": [
            {
                "key": "us-default",
                "market": "US",
                "version_label": "15%",
                "barcode": "900000000002",
                "raw_inci_text": (
                    "Aqua, Ascorbic Acid, Ferulic Acid, Tocopherol, Glycerin, "
                    "Phenoxyethanol"
                ),
                "ingredients": [
                    {"raw_text": "Aqua", "compound_inci": "AQUA"},
                    {
                        "raw_text": "Ascorbic Acid",
                        "is_key_active": True,
                        "active_note": (
                            "Supports brighter-looking skin and helps defend "
                            "against oxidative stress."
                        ),
                    },
                    {"raw_text": "Ferulic Acid"},
                    {"raw_text": "Tocopherol"},
                    {"raw_text": "Glycerin", "compound_inci": "GLYCERIN"},
                    {"raw_text": "Phenoxyethanol", "compound_inci": "PHENOXYETHANOL"},
                ],
            }
        ],
    },
    {
        "key": "daily-moisturizing-sunscreen-spf-50",
        "brand_key": "eltamd",
        "name": "Daily Moisturizing Sunscreen SPF 50",
        "display_name": "EltaMD Daily Moisturizing Sunscreen SPF 50",
        "category": "SPF",
        "description": (
            "A moisturizing broad-spectrum sunscreen for daily protection and "
            "routine compatibility checks."
        ),
        "formulations": [
            {
                "key": "us-default",
                "market": "US",
                "version_label": "SPF 50",
                "barcode": "900000000003",
                "raw_inci_text": (
                    "Aqua, Zinc Oxide, Glycerin, Dimethicone, Tocopherol, "
                    "Phenoxyethanol"
                ),
                "ingredients": [
                    {"raw_text": "Aqua", "compound_inci": "AQUA"},
                    {
                        "raw_text": "Zinc Oxide",
                        "is_key_active": True,
                        "active_note": "Helps protect skin from UVA and UVB exposure.",
                    },
                    {"raw_text": "Glycerin", "compound_inci": "GLYCERIN"},
                    {"raw_text": "Dimethicone", "compound_inci": "DIMETHICONE"},
                    {"raw_text": "Tocopherol"},
                    {"raw_text": "Phenoxyethanol", "compound_inci": "PHENOXYETHANOL"},
                ],
            }
        ],
    },
    {
        "key": "gentle-foaming-cleanser",
        "brand_key": "cerave",
        "name": "Gentle Foaming Cleanser",
        "display_name": "CeraVe Gentle Foaming Cleanser",
        "category": "Cleanser",
        "description": (
            "A gentle foaming cleanser for removing oil while supporting "
            "barrier-friendly routine planning."
        ),
        "formulations": [
            {
                "key": "us-default",
                "market": "US",
                "version_label": "Current",
                "barcode": "900000000004",
                "raw_inci_text": (
                    "Aqua, Glycerin, Niacinamide, Ceramide NP, Phenoxyethanol"
                ),
                "ingredients": [
                    {"raw_text": "Aqua", "compound_inci": "AQUA"},
                    {"raw_text": "Glycerin", "compound_inci": "GLYCERIN"},
                    {
                        "raw_text": "Niacinamide",
                        "compound_inci": "NIACINAMIDE",
                        "active_note": "Helps support the skin barrier during cleansing.",
                    },
                    {
                        "raw_text": "Ceramide NP",
                        "is_key_active": True,
                        "active_note": "Help support the skin barrier during cleansing.",
                    },
                    {"raw_text": "Phenoxyethanol", "compound_inci": "PHENOXYETHANOL"},
                ],
            }
        ],
    },
    {
        "key": "retinol-0-3-squalane",
        "brand_key": "the-ordinary",
        "name": "Retinol 0.3% in Squalane",
        "display_name": "The Ordinary Retinol 0.3% in Squalane",
        "category": "Treatment",
        "description": (
            "A retinol treatment for firmness, texture, and caution-aware "
            "routine matching."
        ),
        "formulations": [
            {
                "key": "global-default",
                "market": "Global",
                "version_label": "0.3%",
                "barcode": "900000000005",
                "raw_inci_text": "Squalane, Retinol, Simmondsia Chinensis Seed Oil",
                "ingredients": [
                    {"raw_text": "Squalane"},
                    {
                        "raw_text": "Retinol",
                        "compound_inci": "RETINOL",
                        "is_key_active": True,
                        "active_note": (
                            "Can support texture and fine line goals, but may be "
                            "irritating for some users."
                        ),
                    },
                    {"raw_text": "Simmondsia Chinensis Seed Oil"},
                ],
            }
        ],
    },
    {
        "key": "toning-solution",
        "brand_key": "pixi",
        "name": "Toning Solution",
        "display_name": "Pixi Toning Solution",
        "category": "Toner",
        "description": (
            "A toner for understanding exfoliating ingredients and how they may "
            "fit into a routine."
        ),
        "formulations": [
            {
                "key": "us-default",
                "market": "US",
                "version_label": "Current",
                "barcode": "900000000006",
                "raw_inci_text": (
                    "Aqua, Glycolic Acid, Aloe Barbadensis Leaf Juice, Glycerin, "
                    "Phenoxyethanol"
                ),
                "ingredients": [
                    {"raw_text": "Aqua", "compound_inci": "AQUA"},
                    {
                        "raw_text": "Glycolic Acid",
                        "is_key_active": True,
                        "active_note": (
                            "Helps smooth the look of uneven texture; may require "
                            "caution for sensitive skin."
                        ),
                    },
                    {
                        "raw_text": "Aloe Barbadensis Leaf Juice",
                        "compound_inci": "ALOE BARBADENSIS LEAF JUICE",
                    },
                    {"raw_text": "Glycerin", "compound_inci": "GLYCERIN"},
                    {"raw_text": "Phenoxyethanol", "compound_inci": "PHENOXYETHANOL"},
                ],
            }
        ],
    },
]

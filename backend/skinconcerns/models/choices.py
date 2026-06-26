from django.db import models


class ConcernGroup(models.TextChoices):
    BREAKOUTS = "breakouts", "Breakouts & pores"
    OIL = "oil", "Oil & shine"
    DRYNESS = "dryness", "Dryness & barrier"
    REDNESS = "redness", "Redness & sensitivity"
    PIGMENT = "pigment", "Tone & marks"
    TEXTURE = "texture", "Texture"
    HAIR_REMOVAL = "hair_removal", "Hair removal"
    SCALP_FLAKING = "scalp_flaking", "Scalp & flakes"
    SUN_PROTECTION = "sun_protection", "Sun protection"
    SAFETY = "safety", "Safety flags"


class ConcernType(models.TextChoices):
    COSMETIC = "cosmetic", "Cosmetic"
    OTC_DRUG_ADJACENT = "otc_drug_adjacent", "OTC drug adjacent"
    MEDICAL_ADJACENT = "medical_adjacent", "Medical adjacent"
    RED_FLAG = "red_flag", "Red flag"


class RecommendationPolicy(models.TextChoices):
    ALLOW = "allow", "Allow"
    ALLOW_WITH_CLAIM_LIMITS = "allow_with_claim_limits", "Allow with claim limits"
    SUPPORTIVE_ONLY = "supportive_only", "Supportive only"
    SUPPRESS = "suppress", "Suppress"


class CopyMode(models.TextChoices):
    NORMAL = "normal", "Normal"
    CAREFUL = "careful", "Careful"
    REFER_OUT = "refer_out", "Refer out"


class AliasType(models.TextChoices):
    CONSUMER = "consumer", "Consumer language"
    MEDICAL_TERM = "medical_term", "Medical term"
    SYMPTOM = "symptom", "Symptom"
    SYNONYM = "synonym", "Synonym"
    MISSPELLING = "misspelling", "Misspelling"


class RuleKind(models.TextChoices):
    RECOMMEND = "recommend", "Recommend"
    AVOID = "avoid", "Avoid"
    PENALIZE = "penalize", "Penalize"
    BOOST = "boost", "Boost"
    REFER = "refer", "Refer"


class RuleTargetType(models.TextChoices):
    PRODUCT_CATEGORY = "product_category", "Product category"
    CHEMICAL_CLASS = "chemical_class", "Chemical class"
    COMPOUND = "compound", "Compound"
    PROPERTY = "property", "Property"
    FREE_TEXT = "free_text", "Free text"


class EvidenceType(models.TextChoices):
    DEFINITION = "definition", "Definition"
    RULE = "rule", "Rule"
    REGULATORY = "regulatory", "Regulatory"
    SAFETY = "safety", "Safety"
    PUBLIC_GUIDANCE = "public_guidance", "Public guidance"
    CLINICAL = "clinical", "Clinical"


class TriggerSeverity(models.TextChoices):
    CAUTION = "caution", "Caution"
    URGENT = "urgent", "Urgent"
    EMERGENCY = "emergency", "Emergency"


class ProfileConcernSource(models.TextChoices):
    USER_SELECTED = "user_selected", "User selected"
    SEARCH_SELECTED = "search_selected", "Search selected"
    DETECTED_FROM_TEXT = "detected_from_text", "Detected from text"
    SYSTEM = "system", "System"

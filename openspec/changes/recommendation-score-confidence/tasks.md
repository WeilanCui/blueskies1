## 1. Confidence computation

- [x] 1.1 `data_confidence(formulation) -> float` helper in `core/profiles/` (resolved fraction; zero-ingredient → 0.0; pending-enrichment cap 0.5) using prefetched ingredients
- [x] 1.2 Band mapping (`high`/`medium`/`low`, thresholds 0.8/0.4) as module constants
- [x] 1.3 `RecommendationMatch` carries `data_confidence` + band

## 2. Ranking

- [x] 2.1 Sort key becomes `(excluded, -final_score, band_tier, name, id)`; verify prefetch avoids extra queries

## 3. API + frontend

- [x] 3.1 Serializer adds `data_confidence` (2dp) and `confidence_band`; frontend types updated
- [x] 3.2 "For You" items + score detail render a "limited ingredient data" indicator for low band

## 4. Tests

- [x] 4.1 Helper: full/partial/zero-ingredient/pending-cap cases
- [x] 4.2 Ranking: resolved-over-unknown at equal score; score dominance over confidence
- [x] 4.3 API shape both endpoints; existing tests green

## 5. Docs

- [x] 5.1 Document confidence semantics (knowledge, not quality) in endpoint docs

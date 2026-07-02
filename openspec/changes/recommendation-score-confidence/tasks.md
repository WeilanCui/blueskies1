## 1. Confidence computation

- [ ] 1.1 `data_confidence(formulation) -> float` helper in `core/profiles/` (resolved fraction; zero-ingredient → 0.0; pending-enrichment cap 0.5) using prefetched ingredients
- [ ] 1.2 Band mapping (`high`/`medium`/`low`, thresholds 0.8/0.4) as module constants
- [ ] 1.3 `RecommendationMatch` carries `data_confidence` + band

## 2. Ranking

- [ ] 2.1 Sort key becomes `(excluded, -final_score, band_tier, name, id)`; verify prefetch avoids extra queries

## 3. API + frontend

- [ ] 3.1 Serializer adds `data_confidence` (2dp) and `confidence_band`; frontend types updated
- [ ] 3.2 "For You" items + score detail render a "limited ingredient data" indicator for low band

## 4. Tests

- [ ] 4.1 Helper: full/partial/zero-ingredient/pending-cap cases
- [ ] 4.2 Ranking: resolved-over-unknown at equal score; score dominance over confidence
- [ ] 4.3 API shape both endpoints; existing tests green

## 5. Docs

- [ ] 5.1 Document confidence semantics (knowledge, not quality) in endpoint docs

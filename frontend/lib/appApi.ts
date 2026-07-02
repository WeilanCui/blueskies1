export type AuthUser = {
  id: number;
  username: string;
  email: string;
  display_name: string;
  has_completed_intake: boolean;
};

export type AuthResponse = {
  user: AuthUser;
};

export type UpdateMePayload = {
  display_name: string;
};

export type SignupPayload = {
  email: string;
  password: string;
  display_name?: string;
};

export type LoginPayload = {
  identifier: string;
  password: string;
};

export type IntakePayload = {
  skin_types: string[];
  fitzpatrick_skin_type: string;
  baseline_sensitivity: number | null;
  concerns: string[];
  goals: string[];
  goals_text: string;
  pregnancy_status: string;
  climate: string;
  routine_notes: string;
  sensitivities: string[];
};

export type ConcernPolicy = {
  recommendation_policy: string;
  copy_mode: string;
  recommendation_allowed: boolean;
  supportive_only: boolean;
  refer_out: boolean;
};

export type SkinConcern = {
  id: number;
  slug: string;
  display_name: string;
  consumer_label: string;
  description: string;
  group: string;
  group_label: string;
  concern_type: string;
  recommendation_policy: string;
  copy_mode: string;
  is_common: boolean;
  is_active: boolean;
};

export type SelectedSkinConcern = {
  id: number;
  concern: SkinConcern;
  source: string;
  confidence: number;
  raw_text: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type SkinConcernGroup = {
  group: string;
  label: string;
  concerns: SkinConcern[];
};

export type SkinConcernListResponse = {
  groups: SkinConcernGroup[];
};

export type SkinConcernSearchResponse = {
  query: string;
  results: SkinConcern[];
};

export type IntakeResponse = {
  profile_id: number;
  skin_profile: null | {
    id: number;
    skin_types: string[];
    fitzpatrick_skin_type: string;
    concerns: SelectedSkinConcern[];
    concern_policy: ConcernPolicy;
    goals: string[];
    pregnancy_status: string;
    baseline_sensitivity: number | null;
    climate: string;
    routine_notes: string;
    captured_at: string;
  };
  sensitivities: string[];
};

export type CatalogIngredient = {
  name: string;
  role: string;
  note: string;
  is_key_active: boolean;
  parse_status: string;
};

export type CatalogProduct = {
  id: string;
  product_id: number;
  formulation_id: number | null;
  brand: string;
  name: string;
  display_name: string;
  category: string;
  description: string;
  enrichment_status: string;
  ingredient_count: number;
  ingredients: CatalogIngredient[];
};

export type RoutineTimeOfDay = "am" | "pm" | "any" | "custom";

export type RoutineItem = {
  id: number;
  position: number;
  routine_step: string;
  custom_step_label: string;
  product: null | {
    id: number;
    brand: string;
    name: string;
    display_name: string;
    category: string;
    image_url: string;
  };
  product_id: number | null;
  formulation: null | {
    id: number;
    product_id: number;
    name: string;
    brand: string;
  };
  formulation_id: number | null;
  raw_product_name: string;
  display_name: string;
  usage_notes: string;
  frequency: string;
  schedule: string;
};

export type Routine = {
  id: number;
  name: string;
  time_of_day: RoutineTimeOfDay;
  custom_time_label: string;
  is_active: boolean;
  notes: string;
  items: RoutineItem[];
  created_at: string;
  updated_at: string;
};

export type RoutineItemPayload = {
  id?: number;
  position: number;
  routine_step: string;
  custom_step_label?: string;
  product_id?: number | null;
  formulation_id?: number | null;
  raw_product_name?: string;
  usage_notes?: string;
  frequency?: string;
  schedule?: string;
};

export type RoutinePayload = {
  name: string;
  time_of_day: RoutineTimeOfDay;
  custom_time_label?: string;
  is_active?: boolean;
  notes?: string;
  items?: RoutineItemPayload[];
};

export type AddRoutineProductPayload = {
  routine_id?: number | null;
  time_of_day?: RoutineTimeOfDay;
  custom_time_label?: string;
  routine_step?: string;
  product_id?: number | null;
  formulation_id?: number | null;
  raw_product_name?: string;
  usage_notes?: string;
  frequency?: string;
  schedule?: string;
};

export type AddRoutineProductResponse = {
  routine: Routine;
  item_id: number;
  created: boolean;
};

export type Location = {
  id: number;
  grid_key: string;
  label: string;
  display_name: string;
  city: string;
  region: string;
  country: string;
  postal_code: string;
  latitude: string | null;
  longitude: string | null;
  timezone: string;
  precision: string;
  source: string;
  source_ref: string;
  created_at: string;
  updated_at: string;
};

export type ProfileLocation = {
  id: number;
  label: string;
  is_default: boolean;
  is_active: boolean;
  share_weather_context: boolean;
  source: string;
  location: Location;
  created_at: string;
  updated_at: string;
};

export type ProfileLocationPayload = {
  label?: string;
  is_default?: boolean;
  is_active?: boolean;
  share_weather_context?: boolean;
  source?: string;
  city?: string;
  region?: string;
  country?: string;
  postal_code?: string;
  latitude?: string | number | null;
  longitude?: string | number | null;
  timezone?: string;
  precision?: string;
};

export type WeatherSnapshot = {
  id: number;
  location: number;
  source: string;
  source_ref: string;
  observed_at: string;
  fetched_at: string;
  expires_at: string;
  uv_index: string | null;
  uv_max: string | null;
  temperature_c: string | null;
  humidity_percent: number | null;
  cloud_cover_percent: number | null;
  air_quality_index: number | null;
  pollen_index: string | null;
  raw_payload: Record<string, unknown>;
  is_fresh: boolean;
  created_at: string;
};

export type LocationContext = {
  profile_location: ProfileLocation | null;
  weather_snapshot: WeatherSnapshot | null;
};

export type DailyProductUse = {
  id: number;
  routine: number | null;
  routine_item: RoutineItem | null;
  product: RoutineItem["product"];
  formulation: RoutineItem["formulation"];
  raw_product_name: string;
  time_of_day: RoutineTimeOfDay;
  routine_step: string;
  notes: string;
  created_at: string;
};

export type DailyCheckIn = {
  id: number;
  checkin_date: string;
  skin_feel: string;
  skin_notes: string;
  symptoms: string[];
  suspected_triggers: string[];
  am_routine_completed: boolean | null;
  pm_routine_completed: boolean | null;
  product_uses: DailyProductUse[];
  completed_routine_item_ids: number[];
  created_at: string;
  updated_at: string;
};

export type TodayCheckInPayload = {
  skin_feel?: string;
  skin_notes?: string;
  symptoms?: string[];
  suspected_triggers?: string[];
  completed_routine_item_ids?: number[];
};

export type ReactionEvent = {
  id: number;
  daily_checkin: number | null;
  routine: number | null;
  routine_item: number | null;
  product: RoutineItem["product"];
  product_id: number | null;
  formulation: RoutineItem["formulation"];
  formulation_id: number | null;
  title: string;
  severity: "mild" | "moderate" | "severe";
  status: "active" | "resolved";
  occurred_on: string;
  resolved_on: string | null;
  symptoms: string[];
  suspected_trigger: string;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type ReactionPayload = {
  daily_checkin?: number | null;
  routine?: number | null;
  routine_item?: number | null;
  product_id?: number | null;
  formulation_id?: number | null;
  title?: string;
  severity?: ReactionEvent["severity"];
  status?: ReactionEvent["status"];
  occurred_on?: string;
  resolved_on?: string | null;
  symptoms?: string[];
  suspected_trigger?: string;
  notes?: string;
};

function getErrorMessage(data: unknown, fallback: string): string {
  if (data && typeof data === "object") {
    const detail = "detail" in data ? data.detail : undefined;
    if (typeof detail === "string") {
      return detail;
    }
    const nonField =
      "non_field_errors" in data ? data.non_field_errors : undefined;
    if (Array.isArray(nonField) && typeof nonField[0] === "string") {
      return nonField[0];
    }
    const firstFieldError = Object.values(data)
      .flatMap((value) => (Array.isArray(value) ? value : [value]))
      .find((value) => typeof value === "string");
    if (typeof firstFieldError === "string") {
      return firstFieldError;
    }
  }
  return fallback;
}

async function requestJson<T>(
  path: string,
  options: RequestInit = {},
  fallbackError = "Request failed.",
): Promise<T> {
  const response = await fetch(path, {
    ...options,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  const data = (await response.json()) as unknown;
  if (!response.ok) {
    throw new Error(getErrorMessage(data, fallbackError));
  }
  return data as T;
}

export function getMe(): Promise<AuthResponse> {
  return requestJson<AuthResponse>("/api/auth/me", {}, "Please log in.");
}

export function updateMe(payload: UpdateMePayload): Promise<AuthResponse> {
  return requestJson<AuthResponse>(
    "/api/auth/me",
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    "Could not update your profile.",
  );
}

export function signup(payload: SignupPayload): Promise<AuthResponse> {
  return requestJson<AuthResponse>(
    "/api/auth/signup",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Could not create your account.",
  );
}

export function login(payload: LoginPayload): Promise<AuthResponse> {
  return requestJson<AuthResponse>(
    "/api/auth/login",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Could not log in.",
  );
}

export function logout(): Promise<{ detail: string }> {
  return requestJson<{ detail: string }>(
    "/api/auth/logout",
    { method: "POST" },
    "Could not log out.",
  );
}

export function getIntake(): Promise<IntakeResponse> {
  return requestJson<IntakeResponse>(
    "/api/intake",
    {},
    "Could not load intake.",
  );
}

export function saveIntake(payload: IntakePayload): Promise<IntakeResponse> {
  return requestJson<IntakeResponse>(
    "/api/intake",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Could not save intake.",
  );
}

export function getSkinConcerns(): Promise<SkinConcernListResponse> {
  return requestJson<SkinConcernListResponse>(
    "/api/skin-concerns",
    {},
    "Could not load skin concerns.",
  );
}

export function searchSkinConcerns(
  query: string,
): Promise<SkinConcernSearchResponse> {
  const suffix = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
  return requestJson<SkinConcernSearchResponse>(
    `/api/skin-concerns/search${suffix}`,
    {},
    "Could not search skin concerns.",
  );
}

export function getCatalogProducts(query = ""): Promise<CatalogProduct[]> {
  const suffix = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
  return requestJson<CatalogProduct[]>(
    `/api/products${suffix}`,
    {},
    "Could not load products.",
  );
}

export function getCatalogProduct(id: string): Promise<CatalogProduct> {
  return requestJson<CatalogProduct>(
    `/api/products/${encodeURIComponent(id)}`,
    {},
    "Could not load product.",
  );
}

export function getRoutines(activeOnly = true): Promise<Routine[]> {
  const suffix = activeOnly ? "?active=true" : "";
  return requestJson<Routine[]>(
    `/api/routines${suffix}`,
    {},
    "Could not load routines.",
  );
}

export function createRoutine(payload: RoutinePayload): Promise<Routine> {
  return requestJson<Routine>(
    "/api/routines",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Could not save routine.",
  );
}

export function updateRoutine(
  id: number,
  payload: RoutinePayload,
): Promise<Routine> {
  return requestJson<Routine>(
    `/api/routines/${id}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
    "Could not update routine.",
  );
}

export function archiveRoutine(id: number): Promise<Routine> {
  return requestJson<Routine>(
    `/api/routines/${id}/archive`,
    { method: "POST" },
    "Could not archive routine.",
  );
}

export function addProductToRoutine(
  payload: AddRoutineProductPayload,
): Promise<AddRoutineProductResponse> {
  return requestJson<AddRoutineProductResponse>(
    "/api/routines/add-product",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Could not add product to routine.",
  );
}

export function getProfileLocations(): Promise<ProfileLocation[]> {
  return requestJson<ProfileLocation[]>(
    "/api/profile-locations",
    {},
    "Could not load profile locations.",
  );
}

export function createProfileLocation(
  payload: ProfileLocationPayload,
): Promise<ProfileLocation> {
  return requestJson<ProfileLocation>(
    "/api/profile-locations",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Could not save location.",
  );
}

export function updateProfileLocation(
  id: number,
  payload: ProfileLocationPayload,
): Promise<ProfileLocation> {
  return requestJson<ProfileLocation>(
    `/api/profile-locations/${id}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    "Could not update location.",
  );
}

export function setDefaultProfileLocation(
  id: number,
): Promise<ProfileLocation> {
  return requestJson<ProfileLocation>(
    `/api/profile-locations/${id}/set-default`,
    { method: "POST" },
    "Could not set default location.",
  );
}

export function getCurrentLocationContext(): Promise<LocationContext> {
  return requestJson<LocationContext>(
    "/api/profile-locations/current-context",
    {},
    "Could not load location context.",
  );
}

export function refreshProfileLocationWeather(
  id: number,
): Promise<LocationContext> {
  return requestJson<LocationContext>(
    `/api/profile-locations/${id}/refresh-weather`,
    { method: "POST" },
    "Could not refresh weather context.",
  );
}

export function getTodayCheckIn(): Promise<DailyCheckIn> {
  return requestJson<DailyCheckIn>(
    "/api/daily-checkins/today",
    {},
    "Could not load today's log.",
  );
}

export function getDailyCheckIns(): Promise<DailyCheckIn[]> {
  return requestJson<DailyCheckIn[]>(
    "/api/daily-checkins",
    {},
    "Could not load routine history.",
  );
}

export function saveTodayCheckIn(
  payload: TodayCheckInPayload,
): Promise<DailyCheckIn> {
  return requestJson<DailyCheckIn>(
    "/api/daily-checkins/today",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Could not save today's log.",
  );
}

export function getReactions(): Promise<ReactionEvent[]> {
  return requestJson<ReactionEvent[]>(
    "/api/reactions",
    {},
    "Could not load reactions.",
  );
}

export function createReaction(
  payload: ReactionPayload,
): Promise<ReactionEvent> {
  return requestJson<ReactionEvent>(
    "/api/reactions",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Could not save reaction.",
  );
}

export function updateReaction(
  id: number,
  payload: ReactionPayload,
): Promise<ReactionEvent> {
  return requestJson<ReactionEvent>(
    `/api/reactions/${id}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    "Could not update reaction.",
  );
}

export type FormulationIngredient = {
  id: number;
  name: string;
  role: string;
  note: string;
  is_key_active: boolean;
  parse_status: string;
  position: number;
};

export type FormulationProduct = {
  id: number;
  brand: string;
  name: string;
  category: string;
};

export type Formulation = {
  id: number;
  product: FormulationProduct;
  barcode: string;
  raw_inci_text: string;
  enrichment_status: string;
  ingredients: FormulationIngredient[];
};

export type BarcodeScanResponse = {
  created: boolean;
  barcode: string;
  formulation: Formulation;
};

export function scanBarcode(barcode: string): Promise<BarcodeScanResponse> {
  return requestJson<BarcodeScanResponse>(
    "/api/products/scan-barcode",
    {
      method: "POST",
      body: JSON.stringify({ barcode }),
    },
    "Could not look up that barcode.",
  );
}

export type ConstraintImpact = {
  constraint_id: number;
  kind: string;
  enforcement: string;
  severity: string;
  target_type: string;
  target: string;
  reason: string;
  score_delta: number;
  source: "constraint" | "concern";
  concern: string | null;
  position_factor: number | null;
  evidence_count: number | null;
  evidence_multiplier: number | null;
};

export type CoverageSummary = {
  concern: string;
  concern_label: string;
  matched: number;
  total: number;
  matched_rules: string[];
  unmatched_rules: string[];
};

export type RecommendationMatch = {
  formulation_id: number;
  product_name: string;
  brand_name: string;
  final_score: number;
  excluded: boolean;
  reasons: string[];
  warnings: ConstraintImpact[];
  penalties: ConstraintImpact[];
  boosts: ConstraintImpact[];
  coverage: CoverageSummary[];
  data_confidence: number;
  confidence_band: "high" | "medium" | "low";
};

export type PaginatedRecommendations = {
  count: number;
  next: string | null;
  previous: string | null;
  results: RecommendationMatch[];
};

export function scoreFormulation(
  formulationId: number,
): Promise<RecommendationMatch> {
  return requestJson<RecommendationMatch>(
    "/api/recommendations/score/",
    {
      method: "POST",
      body: JSON.stringify({ formulation_id: formulationId }),
    },
    "Could not score that formulation.",
  );
}

export function getRankedRecommendations(
  includeExcluded = false,
  page = 1,
): Promise<PaginatedRecommendations> {
  const params = new URLSearchParams();
  if (includeExcluded) {
    params.set("include_excluded", "true");
  }
  if (page > 1) {
    params.set("page", String(page));
  }
  const query = params.toString();
  const path = query
    ? `/api/recommendations/?${query}`
    : "/api/recommendations/";
  return requestJson<PaginatedRecommendations>(
    path,
    {},
    "Could not load recommendations.",
  );
}

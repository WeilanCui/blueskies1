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
  skin_type: string;
  fitzpatrick_skin_type: string;
  baseline_sensitivity: number | null;
  primary_concerns: string[];
  goals: string[];
  goals_text: string;
  pregnancy_status: string;
  climate: string;
  routine_notes: string;
  sensitivities: string[];
};

export type IntakeResponse = {
  profile_id: number;
  skin_profile: null | {
    id: number;
    skin_type: string;
    fitzpatrick_skin_type: string;
    primary_concerns: string[];
    goals: string[];
    pregnancy_status: string;
    baseline_sensitivity: number | null;
    climate: string;
    routine_notes: string;
    captured_at: string;
  };
  sensitivities: string[];
};

function getErrorMessage(data: unknown, fallback: string): string {
  if (data && typeof data === "object") {
    const detail = "detail" in data ? data.detail : undefined;
    if (typeof detail === "string") {
      return detail;
    }
    const nonField = "non_field_errors" in data ? data.non_field_errors : undefined;
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
  return requestJson<IntakeResponse>("/api/intake", {}, "Could not load intake.");
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

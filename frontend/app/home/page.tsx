"use client";

import { ArrowPathIcon, MapPinIcon } from "@heroicons/react/24/outline";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Button } from "../../components/Button";
import {
  createProfileLocation,
  getCurrentLocationContext,
  getIntake,
  getMe,
  refreshProfileLocationWeather,
  type LocationContext,
  type ProfileLocation,
} from "../../lib/appApi";
import styles from "./home.module.css";

const authFreshMs = 5 * 60 * 1000;
const locationContextQueryKey = ["location-context"] as const;
const signalTotal = 8;

const skinTypeLabels: Record<string, string> = {
  combination: "Combination",
  dry: "Dry",
  normal: "Normal",
  oily: "Oily",
  sensitive: "Sensitive",
  unknown: "Not sure",
};

const fitzpatrickLabels: Record<string, string> = {
  not_provided: "Not provided",
  type_i: "Type I",
  type_ii: "Type II",
  type_iii: "Type III",
  type_iv: "Type IV",
  type_v: "Type V",
  type_vi: "Type VI",
};

function displayName(name: string, fallback: string): string {
  return name.trim() || fallback;
}

function formatToken(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatLocation(profileLocation: ProfileLocation): string {
  const location = profileLocation.location;
  return (
    location.display_name ||
    [location.city, location.region, location.postal_code].filter(Boolean).join(", ") ||
    profileLocation.label
  );
}

function numericSnapshotValue(value: string | null | undefined): number | null {
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatUvValue(value: number | null): string {
  if (value === null) {
    return "--";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function getUvRisk(value: number | null): {
  label: string;
  className: string;
} {
  if (value === null) {
    return { label: "Awaiting UV", className: styles.uvUnavailable };
  }
  if (value < 3) {
    return { label: "Low UV", className: styles.uvLow };
  }
  if (value < 6) {
    return { label: "Moderate UV", className: styles.uvModerate };
  }
  if (value < 8) {
    return { label: "High UV", className: styles.uvHigh };
  }
  if (value < 11) {
    return { label: "Very high UV", className: styles.uvVeryHigh };
  }
  return { label: "Extreme UV", className: styles.uvExtreme };
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return "Not available";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function formatTemperature(value: string | null | undefined): string | null {
  const celsius = numericSnapshotValue(value);
  if (celsius === null) {
    return null;
  }
  const fahrenheit = Math.round((celsius * 9) / 5 + 32);
  return `${fahrenheit} F / ${celsius.toFixed(1)} C`;
}

function formatPercent(value: number | null | undefined): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  return `${value}%`;
}

function weatherSourceLabel(source: string | undefined): string {
  const labels: Record<string, string> = {
    epa_uv: "EPA UV",
    weather_api: "Weather API",
    manual: "Manual",
  };
  return source ? labels[source] || formatToken(source) : "Weather";
}

export default function HomePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [locationLabel, setLocationLabel] = useState("Home");
  const [postalCode, setPostalCode] = useState("");
  const [city, setCity] = useState("");
  const [region, setRegion] = useState("");

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
    staleTime: authFreshMs,
  });
  const intakeQuery = useQuery({
    queryKey: ["intake"],
    queryFn: getIntake,
    enabled: meQuery.isSuccess,
    retry: false,
  });
  const locationContextQuery = useQuery({
    queryKey: locationContextQueryKey,
    queryFn: getCurrentLocationContext,
    enabled: meQuery.isSuccess,
    retry: false,
    staleTime: 15 * 60 * 1000,
  });
  const refreshWeatherMutation = useMutation({
    mutationFn: refreshProfileLocationWeather,
    onSuccess: (data) => {
      queryClient.setQueryData<LocationContext>(locationContextQueryKey, data);
    },
  });
  const saveLocationMutation = useMutation({
    mutationFn: async (): Promise<LocationContext> => {
      const profileLocation = await createProfileLocation({
        label: locationLabel.trim() || "Home",
        postal_code: postalCode.trim(),
        city: city.trim(),
        region: region.trim().toUpperCase(),
        country: "US",
        precision: "postal_code",
        is_default: true,
        share_weather_context: true,
        source: "manual",
      });
      try {
        return await refreshProfileLocationWeather(profileLocation.id);
      } catch {
        return { profile_location: profileLocation, weather_snapshot: null };
      }
    },
    onSuccess: (data) => {
      queryClient.setQueryData<LocationContext>(locationContextQueryKey, data);
      setLocationLabel("Home");
      setPostalCode("");
      setCity("");
      setRegion("");
    },
  });
  useEffect(() => {
    if (meQuery.isError) {
      router.replace("/login");
    }
  }, [meQuery.isError, router]);

  if (meQuery.isLoading || meQuery.isError || !meQuery.data) {
    return <p className="detail-muted">Loading your session...</p>;
  }

  const user = meQuery.data.user;
  const skinProfile = intakeQuery.data?.skin_profile;
  const sensitivities = intakeQuery.data?.sensitivities ?? [];
  const locationContext = locationContextQuery.data;
  const profileLocation = locationContext?.profile_location ?? null;
  const weatherSnapshot = locationContext?.weather_snapshot ?? null;
  const uvValue = numericSnapshotValue(
    weatherSnapshot?.uv_index ?? weatherSnapshot?.uv_max,
  );
  const uvRisk = getUvRisk(uvValue);
  const weatherStats = [
    {
      label: "Observed",
      value: formatDateTime(weatherSnapshot?.observed_at),
    },
    {
      label: "UV max",
      value: formatUvValue(
        numericSnapshotValue(weatherSnapshot?.uv_max ?? weatherSnapshot?.uv_index),
      ),
    },
    {
      label: "Temperature",
      value: formatTemperature(weatherSnapshot?.temperature_c),
    },
    {
      label: "Humidity",
      value: formatPercent(weatherSnapshot?.humidity_percent),
    },
    {
      label: "Cloud cover",
      value: formatPercent(weatherSnapshot?.cloud_cover_percent),
    },
  ].filter((item) => item.value !== null);
  const firstName = displayName(user.display_name, user.username).split(" ")[0];
  const primaryConcerns = skinProfile?.primary_concerns ?? [];
  const goals = skinProfile?.goals ?? [];
  const signalCount = [
    skinProfile?.skin_type,
    skinProfile?.fitzpatrick_skin_type &&
      skinProfile.fitzpatrick_skin_type !== "not_provided",
    skinProfile?.baseline_sensitivity !== null &&
      skinProfile?.baseline_sensitivity !== undefined,
    primaryConcerns.length > 0,
    goals.length > 0,
    sensitivities.length > 0,
    profileLocation,
    weatherSnapshot,
  ].filter(Boolean).length;
  const profileVitals = [
    {
      label: "Skin type",
      value: skinProfile
        ? skinTypeLabels[skinProfile.skin_type] || skinProfile.skin_type
        : "Not saved",
    },
    {
      label: "Fitzpatrick",
      value: skinProfile
        ? fitzpatrickLabels[skinProfile.fitzpatrick_skin_type] ||
          skinProfile.fitzpatrick_skin_type
        : "Not saved",
    },
    {
      label: "Sensitivity",
      value:
        skinProfile?.baseline_sensitivity === null ||
        skinProfile?.baseline_sensitivity === undefined
          ? "Not saved"
          : `${skinProfile.baseline_sensitivity}/10`,
    },
  ];
  const nextCards = [
    {
      title: "Scan a product",
      text: "Capture a barcode, product front, or ingredient list from your phone.",
      href: "/scan",
      action: "Open scan",
    },
    {
      title: "Review catalog",
      text: "Browse ingredients and product data while matching logic comes online.",
      href: "/skincareApi",
      action: "Browse",
    },
  ];
  const canSaveLocation = postalCode.trim().length > 0 && !saveLocationMutation.isPending;

  function submitLocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSaveLocation) {
      return;
    }
    saveLocationMutation.mutate();
  }

  return (
    <>
      <div className={styles.homeLayout}>
        <section className={styles.welcomePanel}>
          <div className={styles.welcomeCopy}>
            <div className={styles.todayRow}>
              <span>Today</span>
              <strong>Skin dashboard</strong>
            </div>
            <h1>Hi, {firstName}</h1>
            <p>
              Your saved context is ready for product scans, routine tracking,
              and ingredient fit checks as the app grows.
            </p>
          </div>
          <div className={styles.profileSignalCard}>
            <div className={styles.signalHeader}>
              <span>Personal context</span>
              <strong>
                {signalCount}/{signalTotal} signals
              </strong>
            </div>
            <div className={styles.signalTrack} aria-hidden="true">
              {Array.from({ length: signalTotal }, (_, index) => (
                <span
                  className={
                    index < signalCount
                      ? [styles.signalSegment, styles.signalSegmentActive].join(" ")
                      : styles.signalSegment
                  }
                  key={index}
                />
              ))}
            </div>
            <p>
              Used to personalize future product and regimen analysis. Medical
              concerns still belong with a clinician.
            </p>
          </div>
        </section>

        <section className={styles.dashboardGrid}>
          <div className={styles.primaryColumn}>
            <section className={styles.scanCard}>
              <div className={styles.scanVisual} aria-hidden="true">
                <span className={styles.scanRing} />
                <span className={styles.scanLine} />
                <span className={styles.scanDotOne} />
                <span className={styles.scanDotTwo} />
              </div>
              <div className={styles.scanCopy}>
                <p className="landing-eyebrow">Next action</p>
                <h2>Scan what you are using.</h2>
                <p>
                  Add a product, barcode, ingredient list, or skin-progress
                  photo. This is the main entry point for regimen intelligence.
                </p>
              </div>
              <Link className={styles.actionLink} href="/scan">
                <Button className={styles.actionButton} type="button">
                  Scan or upload
                </Button>
              </Link>
            </section>

            <section className={styles.timelinePanel}>
              <div className={styles.panelHeader}>
                <div>
                  <span>Skin log</span>
                  <h2>Track changes over time.</h2>
                </div>
                <span className={styles.soonBadge}>Soon</span>
              </div>
              <div className={styles.timelineList}>
                <div className={styles.timelineItem}>
                  <span className={styles.timelineMarker} />
                  <div>
                    <strong>Morning check-in</strong>
                    <p>Redness, dryness, breakouts, oil, and texture notes.</p>
                  </div>
                </div>
                <div className={styles.timelineItem}>
                  <span className={styles.timelineMarker} />
                  <div>
                    <strong>Product effect</strong>
                    <p>Connect a skin change to routine use and timing.</p>
                  </div>
                </div>
                <div className={styles.timelineItem}>
                  <span className={styles.timelineMarker} />
                  <div>
                    <strong>Context layer</strong>
                    <p>Weather, location, hormones, and lifestyle signals.</p>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <aside className={styles.sideColumn}>
            <section className={styles.weatherPanel}>
              <div className={styles.panelHeader}>
                <div>
                  <span>Location context</span>
                  <h2>UV and weather</h2>
                </div>
                {profileLocation && (
                  <Button
                    className={styles.refreshButton}
                    type="button"
                    variant="ghost"
                    isDisabled={refreshWeatherMutation.isPending}
                    onPress={() => refreshWeatherMutation.mutate(profileLocation.id)}
                  >
                    <ArrowPathIcon className={styles.buttonIcon} aria-hidden="true" />
                    {refreshWeatherMutation.isPending ? "Refreshing" : "Refresh"}
                  </Button>
                )}
              </div>

              {locationContextQuery.isLoading ? (
                <p className={styles.weatherNote}>Loading location context...</p>
              ) : locationContextQuery.isError ? (
                <p className={styles.weatherError}>Could not load location context.</p>
              ) : profileLocation ? (
                <>
                  <div className={styles.weatherHero}>
                    <div className={[styles.uvDial, uvRisk.className].join(" ")}>
                      <span>UV</span>
                      <strong>{formatUvValue(uvValue)}</strong>
                    </div>
                    <div className={styles.weatherSummary}>
                      <span>
                        <MapPinIcon className={styles.inlineIcon} aria-hidden="true" />
                        {formatLocation(profileLocation)}
                      </span>
                      <strong>{uvRisk.label}</strong>
                      <p>
                        {weatherSnapshot
                          ? `Updated ${formatDateTime(weatherSnapshot.fetched_at)} from ${weatherSourceLabel(weatherSnapshot.source)}.`
                          : profileLocation.share_weather_context
                            ? "UV data will appear after refresh for supported ZIP codes."
                            : "Weather sharing is off for this location."}
                      </p>
                    </div>
                  </div>

                  {weatherSnapshot && (
                    <div className={styles.weatherMetaGrid}>
                      {weatherStats.map((item) => (
                        <div className={styles.weatherMetaItem} key={item.label}>
                          <span>{item.label}</span>
                          <strong>{item.value}</strong>
                        </div>
                      ))}
                    </div>
                  )}

                  {refreshWeatherMutation.isError && (
                    <p className={styles.weatherError}>
                      {refreshWeatherMutation.error instanceof Error
                        ? refreshWeatherMutation.error.message
                        : "Could not refresh weather context."}
                    </p>
                  )}
                </>
              ) : (
                <form className={styles.locationForm} onSubmit={submitLocation}>
                  <p className={styles.weatherNote}>
                    Save a ZIP code to connect UV index to your skin dashboard.
                  </p>
                  <label>
                    <span>Location label</span>
                    <input
                      type="text"
                      value={locationLabel}
                      onChange={(event) => setLocationLabel(event.target.value)}
                      placeholder="Home"
                    />
                  </label>
                  <label>
                    <span>ZIP code</span>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={postalCode}
                      onChange={(event) => setPostalCode(event.target.value)}
                      placeholder="10001"
                    />
                  </label>
                  <div className={styles.locationFormGrid}>
                    <label>
                      <span>City</span>
                      <input
                        type="text"
                        value={city}
                        onChange={(event) => setCity(event.target.value)}
                        placeholder="New York"
                      />
                    </label>
                    <label>
                      <span>State</span>
                      <input
                        type="text"
                        value={region}
                        onChange={(event) => setRegion(event.target.value)}
                        placeholder="NY"
                        maxLength={32}
                      />
                    </label>
                  </div>
                  <Button
                    className={styles.locationSubmitButton}
                    type="submit"
                    isDisabled={!canSaveLocation}
                  >
                    {saveLocationMutation.isPending ? "Saving..." : "Save location"}
                  </Button>
                  {saveLocationMutation.isError && (
                    <p className={styles.weatherError}>
                      {saveLocationMutation.error instanceof Error
                        ? saveLocationMutation.error.message
                        : "Could not save location."}
                    </p>
                  )}
                </form>
              )}
            </section>

            <section className={styles.profilePanel}>
              <div className={styles.panelHeader}>
                <div>
                  <span>Profile snapshot</span>
                  <h2>Current baseline</h2>
                </div>
              </div>
              <div className={styles.vitalList}>
                {profileVitals.map((item) => (
                  <div className={styles.vitalItem} key={item.label}>
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                  </div>
                ))}
              </div>
              <div className={styles.tagList}>
                {primaryConcerns.length > 0 ? (
                  primaryConcerns.slice(0, 6).map((concern) => (
                    <span className="tag" key={concern}>
                      {formatToken(concern)}
                    </span>
                  ))
                ) : (
                  <span className="tag">No concerns saved</span>
                )}
              </div>
            </section>

            <section className={styles.regimenPanel}>
              <div className={styles.panelHeader}>
                <div>
                  <span>Regimen intelligence</span>
                  <h2>What Blueskies will connect</h2>
                </div>
              </div>
              <div className={styles.connectionList}>
                <div>
                  <strong>Products</strong>
                  <span>Formulations, ingredients, and barcodes</span>
                </div>
                <div>
                  <strong>Fit</strong>
                  <span>Goals, constraints, and sensitivities</span>
                </div>
                <div>
                  <strong>Outcomes</strong>
                  <span>Skin state before and after routine changes</span>
                </div>
              </div>
            </section>
          </aside>
        </section>

        <section className={styles.nextGrid}>
          {nextCards.map((card) => (
            <Link className={styles.nextCard} href={card.href} key={card.title}>
              <div>
                <h2>{card.title}</h2>
                <p>{card.text}</p>
              </div>
              <span>{card.action}</span>
            </Link>
          ))}
        </section>

        <section className={styles.notesPanel}>
          <div className={styles.panelHeader}>
            <div>
              <span>Saved notes</span>
              <h2>Routine context</h2>
            </div>
          </div>
          <p>{skinProfile?.routine_notes || "No routine notes have been added yet."}</p>
          <div className={styles.tagList}>
            {goals.length > 0 ? (
              goals.slice(0, 4).map((goal) => (
                <span className="chip" key={goal}>
                  {goal}
                </span>
              ))
            ) : (
              <span className="chip">No goals saved</span>
            )}
            {sensitivities.length > 0 &&
              sensitivities.slice(0, 4).map((item) => (
                <span className="badge" key={item}>
                  {item}
                </span>
              ))}
          </div>
        </section>
      </div>

      <div className={styles.mobileActionDock}>
        <Link href="/scan">
          <Button className={styles.mobileDockButton} type="button">
            Scan or upload
          </Button>
        </Link>
      </div>
    </>
  );
}

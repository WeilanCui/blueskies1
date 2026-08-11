"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useState } from "react";

import {
  createProfileLocation,
  getCurrentLocationContext,
  type LocationContext,
  type ProfileLocation,
  refreshProfileLocationWeather,
} from "../../lib/appApi";
import styles from "./home.module.css";

const locationContextQueryKey = ["location-context"] as const;

type WeatherStat = {
  label: string;
  value: string;
};

function formatToken(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function formatLocation(profileLocation: ProfileLocation): string {
  const location = profileLocation.location;
  return (
    location.display_name ||
    [location.city, location.region, location.postal_code]
      .filter(Boolean)
      .join(", ") ||
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

export function formatUvValue(value: number | null): string {
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

export function useLocationContextData(
  enabled: boolean,
  onContextChange?: (context: LocationContext | undefined) => void,
) {
  const queryClient = useQueryClient();
  const locationContextQuery = useQuery({
    queryKey: locationContextQueryKey,
    queryFn: getCurrentLocationContext,
    enabled,
    retry: false,
    staleTime: 15 * 60 * 1000,
  });
  const refreshWeatherMutation = useMutation({
    mutationFn: refreshProfileLocationWeather,
    onSuccess: (data) => {
      queryClient.setQueryData<LocationContext>(locationContextQueryKey, data);
    },
  });

  useEffect(() => {
    onContextChange?.(locationContextQuery.data);
  }, [locationContextQuery.data, onContextChange]);

  return { locationContextQuery, refreshWeatherMutation };
}

export function useLocationForm() {
  const queryClient = useQueryClient();
  const [locationLabel, setLocationLabel] = useState("Home");
  const [postalCode, setPostalCode] = useState("");
  const [city, setCity] = useState("");
  const [region, setRegion] = useState("");

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
  const canSaveLocation =
    postalCode.trim().length > 0 && !saveLocationMutation.isPending;

  function submitLocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSaveLocation) {
      return;
    }
    saveLocationMutation.mutate();
  }

  return {
    canSaveLocation,
    city,
    locationLabel,
    postalCode,
    region,
    saveLocationMutation,
    setCity,
    setLocationLabel,
    setPostalCode,
    setRegion,
    submitLocation,
  };
}

export function getWeatherDisplay(
  locationContext: LocationContext | undefined,
): {
  profileLocation: ProfileLocation | null;
  summaryText: string;
  uvRisk: ReturnType<typeof getUvRisk>;
  uvValue: number | null;
  weatherSnapshot: LocationContext["weather_snapshot"] | null;
  weatherStats: WeatherStat[];
} {
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
        numericSnapshotValue(
          weatherSnapshot?.uv_max ?? weatherSnapshot?.uv_index,
        ),
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
  ].filter((item): item is WeatherStat => item.value !== null);
  const summaryText = weatherSnapshot
    ? `Updated ${formatDateTime(weatherSnapshot.fetched_at)} from ${weatherSourceLabel(weatherSnapshot.source)}.`
    : profileLocation?.share_weather_context
      ? "UV data will appear after refresh for supported ZIP codes."
      : "Weather sharing is off for this location.";

  return {
    profileLocation,
    summaryText,
    uvRisk,
    uvValue,
    weatherSnapshot,
    weatherStats,
  };
}

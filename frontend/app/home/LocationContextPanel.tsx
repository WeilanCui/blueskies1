"use client";

import { ArrowPathIcon, MapPinIcon } from "@heroicons/react/24/outline";
import { useMemo } from "react";

import { Button } from "../../components/Button";
import {
  type LocationContext,
} from "../../lib/appApi";
import styles from "./home.module.css";
import { useLocationContextData, useLocationForm, getWeatherDisplay, formatUvValue, formatLocation } from "./locationHooks";

type LocationContextPanelProps = {
  enabled: boolean;
  onContextChange?: (context: LocationContext | undefined) => void;
};

export function LocationContextPanel({
  enabled,
  onContextChange,
}: LocationContextPanelProps) {
  const { locationContextQuery, refreshWeatherMutation } =
    useLocationContextData(enabled, onContextChange);
  const locationForm = useLocationForm();
  const {
    profileLocation,
    summaryText,
    uvRisk,
    uvValue,
    weatherSnapshot,
    weatherStats,
  } = useMemo(
    () => getWeatherDisplay(locationContextQuery.data),
    [locationContextQuery.data],
  );

  return (
    <section className={styles.weatherPanel}>
      <div className={styles.panelHeader}>
        <div>
          <span>UV and weather</span>
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
        <p className={styles.weatherNote}>Loading location info...</p>
      ) : locationContextQuery.isError ? (
        <p className={styles.weatherError}>Could not load location info.</p>
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
              {/* <p>{summaryText}</p> */}
              
            </div>
          </div>

          {weatherSnapshot && (
            <div className={styles.weatherMetaGrid}>
              {weatherStats.map((item) => (
                <div className={[styles.uvDial, uvRisk.className].join(" ")} key={item.label}>
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
        <form
          className={styles.locationForm}
          onSubmit={locationForm.submitLocation}
        >
          <p className={styles.weatherNote}>
            Save a ZIP code to connect UV index to your skin dashboard.
          </p>
          <label>
            <span>Location label</span>
            <input
              type="text"
              value={locationForm.locationLabel}
              onChange={(event) =>
                locationForm.setLocationLabel(event.target.value)
              }
              placeholder="Home"
            />
          </label>
          <label>
            <span>ZIP code</span>
            <input
              type="text"
              inputMode="numeric"
              value={locationForm.postalCode}
              onChange={(event) =>
                locationForm.setPostalCode(event.target.value)
              }
              placeholder="10001"
            />
          </label>
          <div className={styles.locationFormGrid}>
            <label>
              <span>City</span>
              <input
                type="text"
                value={locationForm.city}
                onChange={(event) => locationForm.setCity(event.target.value)}
                placeholder="New York"
              />
            </label>
            <label>
              <span>State</span>
              <input
                type="text"
                value={locationForm.region}
                onChange={(event) => locationForm.setRegion(event.target.value)}
                placeholder="NY"
                maxLength={32}
              />
            </label>
          </div>
          <Button
            className={styles.locationSubmitButton}
            type="submit"
            isDisabled={!locationForm.canSaveLocation}
          >
            {locationForm.saveLocationMutation.isPending
              ? "Saving..."
              : "Save location"}
          </Button>
          {locationForm.saveLocationMutation.isError && (
            <p className={styles.weatherError}>
              {locationForm.saveLocationMutation.error instanceof Error
                ? locationForm.saveLocationMutation.error.message
                : "Could not save location."}
            </p>
          )}
        </form>
      )}
    </section>
  );
}

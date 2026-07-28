import { useMemo } from "react";

import { concernZones } from "../lib/profileForm";

export function useConcernZones(concerns: string[]): string[] {
  return useMemo(() => {
    const zones = new Set<string>();
    for (const concern of concerns) {
      for (const zone of concernZones[concern] ?? []) {
        zones.add(zone);
      }
    }
    return Array.from(zones);
  }, [concerns]);
}

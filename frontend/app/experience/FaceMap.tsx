import styles from "./FaceMap.module.css";

type FaceZone = {
  id: string;
  label: string;
  cx: number;
  cy: number;
  r: number;
};

const ZONES: FaceZone[] = [
  { id: "forehead", label: "Forehead", cx: 150, cy: 72, r: 38 },
  { id: "eyes", label: "Eye area", cx: 150, cy: 118, r: 52 },
  { id: "cheeks", label: "Cheeks", cx: 150, cy: 168, r: 58 },
  { id: "nose", label: "Nose", cx: 150, cy: 155, r: 18 },
  { id: "chin", label: "Chin", cx: 150, cy: 228, r: 32 },
  { id: "lips", label: "Lips", cx: 150, cy: 198, r: 16 },
];

export default function FaceMap({
  activeZones,
  analyzing = false,
}: {
  activeZones: string[];
  analyzing?: boolean;
}) {
  return (
    <div className={styles.faceMap}>
      <svg viewBox="0 0 300 300" aria-label="Facial analysis map">
        <ellipse
          cx="150"
          cy="155"
          rx="95"
          ry="118"
          className={styles.faceOutline}
        />
        <ellipse
          cx="118"
          cy="118"
          rx="14"
          ry="10"
          className={styles.faceFeature}
        />
        <ellipse
          cx="182"
          cy="118"
          rx="14"
          ry="10"
          className={styles.faceFeature}
        />
        <path
          d="M 128 198 Q 150 210 172 198"
          className={styles.faceFeature}
          fill="none"
          strokeWidth="2"
        />

        {ZONES.map((zone) => {
          const active = activeZones.includes(zone.id);
          return (
            <g key={zone.id}>
              <circle
                cx={zone.cx}
                cy={zone.cy}
                r={zone.r}
                className={
                  active
                    ? [styles.faceZone, styles.faceZoneActive].join(" ")
                    : styles.faceZone
                }
              />
              {active && (
                <text
                  x={zone.cx}
                  y={zone.cy + 4}
                  textAnchor="middle"
                  className={styles.faceZoneLabel}
                >
                  {zone.label}
                </text>
              )}
            </g>
          );
        })}

        {analyzing && (
          <line
            x1="20"
            y1="40"
            x2="280"
            y2="40"
            className={styles.faceScanLine}
          >
            <animate
              attributeName="y1"
              dur="1.4s"
              repeatCount="indefinite"
              values="40;260;40"
            />
            <animate
              attributeName="y2"
              dur="1.4s"
              repeatCount="indefinite"
              values="40;260;40"
            />
          </line>
        )}
      </svg>

      <ul className={styles.faceLegend}>
        {activeZones.length === 0 ? (
          <li className={styles.emptyLegend}>
            Upload a photo and complete intake to see target areas.
          </li>
        ) : (
          activeZones.map((zoneId) => {
            const zone = ZONES.find((item) => item.id === zoneId);
            return zone ? <li key={zoneId}>{zone.label}</li> : null;
          })
        )}
      </ul>
    </div>
  );
}

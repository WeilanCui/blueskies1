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
    <div className={`face-map ${analyzing ? "face-map-analyzing" : ""}`}>
      <svg viewBox="0 0 300 300" aria-label="Facial analysis map">
        <ellipse cx="150" cy="155" rx="95" ry="118" className="face-outline" />
        <ellipse cx="118" cy="118" rx="14" ry="10" className="face-feature" />
        <ellipse cx="182" cy="118" rx="14" ry="10" className="face-feature" />
        <path
          d="M 128 198 Q 150 210 172 198"
          className="face-feature"
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
                className={active ? "face-zone face-zone-active" : "face-zone"}
              />
              {active && (
                <text
                  x={zone.cx}
                  y={zone.cy + 4}
                  textAnchor="middle"
                  className="face-zone-label"
                >
                  {zone.label}
                </text>
              )}
            </g>
          );
        })}

        {analyzing && (
          <line x1="20" y1="40" x2="280" y2="40" className="face-scan-line">
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

      <ul className="face-legend">
        {activeZones.length === 0 ? (
          <li className="detail-muted">Upload a photo and complete intake to see target areas.</li>
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

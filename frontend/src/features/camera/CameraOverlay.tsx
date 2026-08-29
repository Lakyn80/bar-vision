/**
 * Compact guide for a tall glass mug — sized to fit inside the preview
 * without overflowing the screen.
 */
export function CameraOverlay() {
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox="0 0 100 100"
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
    >
      {/* Soft vignette; keep center clear */}
      <defs>
        <mask id="guide-hole">
          <rect width="100" height="100" fill="white" />
          <rect x="38" y="18" width="24" height="64" rx="2" fill="black" />
        </mask>
      </defs>

      <rect
        width="100"
        height="100"
        fill="rgba(0,0,0,0.35)"
        mask="url(#guide-hole)"
      />

      {/* Compact guide box (~24% width × 64% height) */}
      <rect
        x="38"
        y="18"
        width="24"
        height="64"
        fill="none"
        stroke="#fafafa"
        strokeWidth="0.7"
        strokeDasharray="1.8 1.2"
        vectorEffect="non-scaling-stroke"
      />

      {/* Mug body — narrow enough to fit a real glass in frame */}
      <path
        d="M41 22
           H59
           V25
           L60.5 30
           V70
           C60.5 78, 39.5 78, 39.5 70
           V30
           L41 25
           Z"
        fill="none"
        stroke="#4ade80"
        strokeWidth="1.2"
        vectorEffect="non-scaling-stroke"
      />

      {/* Small handle on the left */}
      <path
        d="M41 38
           C35 40, 35 56, 41 58"
        fill="none"
        stroke="#4ade80"
        strokeWidth="1.2"
        vectorEffect="non-scaling-stroke"
      />

      {/* 0.5 l mark zone */}
      <line
        x1="42.5"
        y1="28"
        x2="57.5"
        y2="28"
        stroke="#a1a1aa"
        strokeWidth="0.6"
        strokeDasharray="1.2 1.2"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

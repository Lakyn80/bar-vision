/** Small mug guide centered in the preview (~18% × 48% of frame). */
export function CameraOverlay() {
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <defs>
        <mask id="guide-hole">
          <rect width="100" height="100" fill="white" />
          <rect x="41" y="26" width="18" height="48" rx="1.5" fill="black" />
        </mask>
      </defs>

      <rect
        width="100"
        height="100"
        fill="rgba(0,0,0,0.4)"
        mask="url(#guide-hole)"
      />

      <rect
        x="41"
        y="26"
        width="18"
        height="48"
        fill="none"
        stroke="#fafafa"
        strokeWidth="0.6"
        strokeDasharray="1.5 1"
        vectorEffect="non-scaling-stroke"
      />

      <path
        d="M43.5 29 H56.5 V31.5 L57.5 35 V64 C57.5 70, 42.5 70, 42.5 64 V35 L43.5 31.5 Z"
        fill="none"
        stroke="#4ade80"
        strokeWidth="1.1"
        vectorEffect="non-scaling-stroke"
      />

      <path
        d="M43.5 40 C39 41.5, 39 54, 43.5 55.5"
        fill="none"
        stroke="#4ade80"
        strokeWidth="1.1"
        vectorEffect="non-scaling-stroke"
      />

      <line
        x1="44.5"
        y1="33"
        x2="55.5"
        y2="33"
        stroke="#a1a1aa"
        strokeWidth="0.5"
        strokeDasharray="1 1"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

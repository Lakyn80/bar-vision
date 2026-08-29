/** Medium mug guide — large enough to aim, still fully on-screen. */
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
          <rect x="36" y="20" width="28" height="60" rx="2" fill="black" />
        </mask>
      </defs>

      <rect
        width="100"
        height="100"
        fill="rgba(0,0,0,0.38)"
        mask="url(#guide-hole)"
      />

      <rect
        x="36"
        y="20"
        width="28"
        height="60"
        fill="none"
        stroke="#fafafa"
        strokeWidth="0.7"
        strokeDasharray="1.8 1.2"
        vectorEffect="non-scaling-stroke"
      />

      <path
        d="M40 24 H60 V27 L61.5 32 V70 C61.5 78, 38.5 78, 38.5 70 V32 L40 27 Z"
        fill="none"
        stroke="#4ade80"
        strokeWidth="1.3"
        vectorEffect="non-scaling-stroke"
      />

      <path
        d="M40 40 C34 42, 34 58, 40 60"
        fill="none"
        stroke="#4ade80"
        strokeWidth="1.3"
        vectorEffect="non-scaling-stroke"
      />

      <line
        x1="41.5"
        y1="30"
        x2="58.5"
        y2="30"
        stroke="#a1a1aa"
        strokeWidth="0.6"
        strokeDasharray="1.2 1.2"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export function CameraOverlay() {
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <rect
        x="2"
        y="2"
        width="96"
        height="96"
        fill="none"
        stroke="rgba(0,0,0,0.45)"
        strokeWidth="4"
      />

      <path
        d="M42 12
           C42 8, 58 8, 58 12
           L62 22
           L64 78
           C64 88, 36 88, 36 78
           L38 22
           Z"
        fill="none"
        stroke="#fafafa"
        strokeWidth="1.2"
        vectorEffect="non-scaling-stroke"
      />

      <line
        x1="40"
        y1="30"
        x2="60"
        y2="30"
        stroke="#a1a1aa"
        strokeWidth="0.6"
        strokeDasharray="2 2"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

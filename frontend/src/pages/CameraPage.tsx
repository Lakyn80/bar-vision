import { Link } from "react-router";

import { CameraOverlay } from "../features/camera/CameraOverlay";
import { useCamera } from "../features/camera/useCamera";


export function CameraPage() {
  const {
    videoRef,
    status,
    errorMessage,
    capturedDataUrl,
    startCamera,
    stopCamera,
    captureFrame,
    clearCapture,
  } = useCamera();

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-4 bg-zinc-950 p-4 text-white">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Camera</h1>
          <p className="text-sm text-zinc-400">
            Align the bottle with the outline, then capture.
          </p>
        </div>

        <Link
          to="/"
          className="text-sm text-zinc-300 underline"
        >
          Home
        </Link>
      </header>

      <section className="relative aspect-[3/4] overflow-hidden rounded-2xl border border-zinc-800 bg-black">
        <video
          ref={videoRef}
          className="h-full w-full object-cover"
          playsInline
          muted
          autoPlay
        />

        <CameraOverlay />

        {capturedDataUrl ? (
          <img
            src={capturedDataUrl}
            alt="Captured bottle frame"
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : null}
      </section>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-3 text-sm">
        <div className="text-zinc-500">Status</div>
        <div className="mt-1 font-mono">{status}</div>
        {errorMessage ? (
          <div className="mt-2 text-red-400">{errorMessage}</div>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => {
            void startCamera();
          }}
          className="rounded-xl bg-white px-4 py-3 text-sm font-medium text-zinc-950"
        >
          Open camera
        </button>

        <button
          type="button"
          onClick={captureFrame}
          disabled={status !== "ready" || Boolean(capturedDataUrl)}
          className="rounded-xl border border-zinc-700 px-4 py-3 text-sm disabled:opacity-40"
        >
          Capture
        </button>

        <button
          type="button"
          onClick={clearCapture}
          disabled={!capturedDataUrl}
          className="rounded-xl border border-zinc-700 px-4 py-3 text-sm disabled:opacity-40"
        >
          Retake
        </button>

        <button
          type="button"
          onClick={stopCamera}
          className="rounded-xl border border-zinc-700 px-4 py-3 text-sm"
        >
          Stop
        </button>
      </div>
    </main>
  );
}

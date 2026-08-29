import { useState } from "react";
import { Link } from "react-router";

import { uploadMeasurementDraftFromDataUrl } from "../api/measurements";
import { CameraOverlay } from "../features/camera/CameraOverlay";
import { useCamera } from "../features/camera/useCamera";
import { useFrameGuidance } from "../features/camera/useFrameGuidance";


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

  const guidance = useFrameGuidance({
    videoRef,
    enabled: status === "ready" && !capturedDataUrl,
  });

  const [uploadState, setUploadState] = useState<string>("idle");
  const [uploadDetail, setUploadDetail] = useState<string | null>(null);

  // Guidance is advisory — do not hard-block capture (desktop webcams rarely
  // hit READY with the bottle heuristics).
  const canCapture = status === "ready";

  const onUpload = async () => {
    if (!capturedDataUrl) {
      return;
    }

    setUploadState("uploading");
    setUploadDetail(null);

    try {
      const result = await uploadMeasurementDraftFromDataUrl(capturedDataUrl);
      setUploadState("uploaded");
      setUploadDetail(
        `${result.id} · ${result.original_image_key ?? "no-key"}`,
      );
    } catch (error) {
      setUploadState("error");
      setUploadDetail(
        error instanceof Error ? error.message : "Upload failed.",
      );
    }
  };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-4 bg-zinc-950 p-4 text-white">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Camera</h1>
          <p className="text-sm text-zinc-400">
            Put the glass inside the green outline, then Capture.
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
          className="h-full w-full object-contain"
          playsInline
          muted
          autoPlay
        />

        <CameraOverlay />

        {capturedDataUrl ? (
          <img
            src={capturedDataUrl}
            alt="Captured glass frame"
            className="absolute inset-0 h-full w-full object-contain bg-black"
          />
        ) : null}

        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 to-transparent p-4">
          <div className="text-center font-mono text-lg tracking-wide">
            {capturedDataUrl ? "CAPTURED" : guidance}
          </div>
          <div className="mt-1 text-center text-xs text-zinc-300">
            {capturedDataUrl
              ? "Use Upload draft or Retake."
              : "Green outline = target. Capture works even if guidance is not READY."}
          </div>
        </div>
      </section>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-3 text-sm">
        <div className="text-zinc-500">Status</div>
        <div className="mt-1 font-mono">{status}</div>
        <div className="mt-3 text-zinc-500">Guidance</div>
        <div className="mt-1 font-mono">{guidance}</div>
        <div className="mt-3 text-zinc-500">Upload</div>
        <div className="mt-1 font-mono">{uploadState}</div>
        {uploadDetail ? (
          <div className="mt-2 break-all text-zinc-400">{uploadDetail}</div>
        ) : null}
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
          disabled={!canCapture || Boolean(capturedDataUrl)}
          className={
            canCapture && !capturedDataUrl
              ? "rounded-xl bg-emerald-400 px-4 py-3 text-sm font-semibold text-zinc-950"
              : "rounded-xl border border-zinc-700 px-4 py-3 text-sm disabled:opacity-40"
          }
        >
          Capture
        </button>

        <button
          type="button"
          onClick={() => {
            void onUpload();
          }}
          disabled={!capturedDataUrl || uploadState === "uploading"}
          className="rounded-xl border border-zinc-700 px-4 py-3 text-sm disabled:opacity-40"
        >
          Upload draft
        </button>

        <button
          type="button"
          onClick={() => {
            clearCapture();
            setUploadState("idle");
            setUploadDetail(null);
          }}
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

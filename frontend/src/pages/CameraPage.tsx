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

  const frame = useFrameGuidance({
    videoRef,
    enabled: status === "ready" && !capturedDataUrl,
  });

  const [uploadState, setUploadState] = useState<string>("idle");
  const [uploadDetail, setUploadDetail] = useState<string | null>(null);

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
    <main className="mx-auto flex h-[100dvh] w-full max-w-xl flex-col gap-2 bg-zinc-950 p-3 text-white sm:max-w-2xl sm:gap-3 sm:p-4">
      <header className="flex shrink-0 items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold sm:text-2xl">Camera</h1>
          <p className="text-xs text-zinc-400 sm:text-sm">
            Hold the glass in view — outline tracks it and turns green when locked.
          </p>
        </div>
        <Link to="/" className="text-sm text-zinc-300 underline">
          Home
        </Link>
      </header>

      <div className="flex min-h-0 flex-1 items-center justify-center">
        <section className="relative aspect-[3/4] h-full max-h-full w-auto max-w-full overflow-hidden rounded-xl border border-zinc-800 bg-black">
          <video
            ref={videoRef}
            className="absolute inset-0 h-full w-full object-cover"
            playsInline
            muted
            autoPlay
          />

          <CameraOverlay
            vesselBox={frame.vesselBox}
            locked={frame.locked}
          />

          {capturedDataUrl ? (
            <img
              src={capturedDataUrl}
              alt="Captured glass frame"
              className="absolute inset-0 h-full w-full object-cover"
            />
          ) : null}

          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent px-3 py-2.5">
            <div className="text-center font-mono text-base tracking-wide sm:text-lg">
              {capturedDataUrl
                ? "CAPTURED"
                : frame.locked
                  ? "LOCKED — Capture"
                  : frame.guidance}
            </div>
          </div>
        </section>
      </div>

      <div className="shrink-0 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs sm:text-sm">
        <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono">
          <span>cam:{status}</span>
          <span>guide:{frame.guidance}</span>
          <span>lock:{frame.locked ? "yes" : "no"}</span>
          <span>up:{uploadState}</span>
        </div>
        {uploadDetail ? (
          <div className="mt-1 break-all text-zinc-400">{uploadDetail}</div>
        ) : null}
        {errorMessage ? (
          <div className="mt-1 text-red-400">{errorMessage}</div>
        ) : null}
      </div>

      <div className="flex shrink-0 flex-wrap gap-2 pb-[env(safe-area-inset-bottom)]">
        <button
          type="button"
          onClick={() => {
            void startCamera();
          }}
          className="rounded-lg bg-white px-3 py-2.5 text-sm font-medium text-zinc-950"
        >
          Open camera
        </button>

        <button
          type="button"
          onClick={captureFrame}
          disabled={!canCapture || Boolean(capturedDataUrl)}
          className={
            canCapture && !capturedDataUrl
              ? "rounded-lg bg-emerald-400 px-3 py-2.5 text-sm font-semibold text-zinc-950"
              : "rounded-lg border border-zinc-700 px-3 py-2.5 text-sm disabled:opacity-40"
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
          className="rounded-lg border border-zinc-700 px-3 py-2.5 text-sm disabled:opacity-40"
        >
          Upload
        </button>

        <button
          type="button"
          onClick={() => {
            clearCapture();
            setUploadState("idle");
            setUploadDetail(null);
          }}
          disabled={!capturedDataUrl}
          className="rounded-lg border border-zinc-700 px-3 py-2.5 text-sm disabled:opacity-40"
        >
          Retake
        </button>

        <button
          type="button"
          onClick={stopCamera}
          className="rounded-lg border border-zinc-700 px-3 py-2.5 text-sm"
        >
          Stop
        </button>
      </div>
    </main>
  );
}

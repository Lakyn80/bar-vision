import { requireAccessToken } from "./auth";


export type MeasurementDraftResponse = {
  id: string;
  status: string;
  measurement_type: string;
  original_image_key: string | null;
};


function dataUrlToBlob(dataUrl: string): Blob {
  const [meta, content] = dataUrl.split(",", 2);
  const mimeMatch = /data:(.*?);base64/.exec(meta);
  const mime = mimeMatch?.[1] ?? "image/jpeg";
  const binary = atob(content);
  const bytes = new Uint8Array(binary.length);

  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }

  return new Blob([bytes], { type: mime });
}


export async function uploadMeasurementDraftFromDataUrl(
  dataUrl: string,
): Promise<MeasurementDraftResponse> {
  const token = requireAccessToken();
  const blob = dataUrlToBlob(dataUrl);
  const form = new FormData();
  form.append("file", blob, "capture.jpg");

  const response = await fetch("/api/v1/measurements/draft", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: form,
  });

  if (!response.ok) {
    throw new Error(`Upload failed with HTTP ${response.status}`);
  }

  return response.json() as Promise<MeasurementDraftResponse>;
}

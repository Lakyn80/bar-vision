export type HealthResponse = {
  status: string;
};


export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/v1/health");

  if (!response.ok) {
    throw new Error(
      `Health request failed with HTTP ${response.status}`,
    );
  }

  return response.json() as Promise<HealthResponse>;
}
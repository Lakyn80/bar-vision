import { useEffect, useState } from "react";


type HealthResponse = {
  status: string;
};


export default function App() {
  const [backendStatus, setBackendStatus] =
    useState("checking");

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch("/api/v1/health");

        if (!response.ok) {
          throw new Error();
        }

        const data =
          (await response.json()) as HealthResponse;

        setBackendStatus(data.status);
      } catch {
        setBackendStatus("error");
      }
    };

    void checkBackend();
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 p-6 text-white">
      <section className="w-full max-w-xl rounded-2xl border border-zinc-800 bg-zinc-900 p-8">
        <h1 className="text-3xl font-semibold">
          Bar Vision
        </h1>

        <p className="mt-3 text-zinc-400">
          Docker foundation
        </p>

        <div className="mt-8 rounded-xl bg-zinc-950 p-5">
          <div className="text-sm text-zinc-500">
            Backend status
          </div>

          <div className="mt-2 font-mono text-lg">
            {backendStatus}
          </div>
        </div>
      </section>
    </main>
  );
}
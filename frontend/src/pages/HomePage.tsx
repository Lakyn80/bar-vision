import { useQuery } from "@tanstack/react-query";

import { getHealth } from "../api/health";


export function HomePage() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
  });

  let status = "checking";

  if (healthQuery.isSuccess) {
    status = healthQuery.data.status;
  }

  if (healthQuery.isError) {
    status = "error";
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 p-6 text-white">
      <section className="w-full max-w-xl rounded-2xl border border-zinc-800 bg-zinc-900 p-8">
        <h1 className="text-3xl font-semibold">
          Bar Vision
        </h1>

        <p className="mt-3 text-zinc-400">
          PWA foundation
        </p>

        <div className="mt-8 rounded-xl bg-zinc-950 p-5">
          <div className="text-sm text-zinc-500">
            Backend status
          </div>

          <div className="mt-2 font-mono text-lg">
            {status}
          </div>
        </div>
      </section>
    </main>
  );
}
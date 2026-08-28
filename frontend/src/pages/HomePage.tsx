import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import { login } from "../api/auth";
import { getAccessToken, clearAccessToken } from "../api/auth-storage";
import { getHealth } from "../api/health";


export function HomePage() {
  const [email, setEmail] = useState("uploader@example.com");
  const [password, setPassword] = useState("CorrectPassword1!");
  const [authMessage, setAuthMessage] = useState<string | null>(null);
  const [hasToken, setHasToken] = useState(Boolean(getAccessToken()));

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

  const onLogin = async (event: FormEvent) => {
    event.preventDefault();
    setAuthMessage(null);

    try {
      await login(email, password);
      setHasToken(true);
      setAuthMessage("Logged in.");
    } catch {
      setHasToken(false);
      setAuthMessage("Login failed.");
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 p-6 text-white">
      <section className="w-full max-w-xl rounded-2xl border border-zinc-800 bg-zinc-900 p-8">
        <h1 className="text-3xl font-semibold">
          Bar Vision
        </h1>

        <p className="mt-3 text-zinc-400">
          Capture and upload bottle measurements.
        </p>

        <div className="mt-8 rounded-xl bg-zinc-950 p-5">
          <div className="text-sm text-zinc-500">
            Backend status
          </div>

          <div className="mt-2 font-mono text-lg">
            {status}
          </div>
        </div>

        <form
          className="mt-8 space-y-3"
          onSubmit={(event) => {
            void onLogin(event);
          }}
        >
          <input
            className="w-full rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="Email"
            type="email"
            required
          />
          <input
            className="w-full rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Password"
            type="password"
            required
          />
          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              className="rounded-xl bg-white px-4 py-3 text-sm font-medium text-zinc-950"
            >
              Login
            </button>
            <button
              type="button"
              className="rounded-xl border border-zinc-700 px-4 py-3 text-sm"
              onClick={() => {
                clearAccessToken();
                setHasToken(false);
                setAuthMessage("Logged out.");
              }}
            >
              Logout
            </button>
          </div>
        </form>

        <div className="mt-3 font-mono text-sm text-zinc-400">
          Auth: {hasToken ? "token present" : "no token"}
          {authMessage ? ` · ${authMessage}` : ""}
        </div>

        <Link
          to="/camera"
          className="mt-8 inline-flex rounded-xl bg-white px-4 py-3 text-sm font-medium text-zinc-950"
        >
          Open camera
        </Link>
      </section>
    </main>
  );
}

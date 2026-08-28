import { Link } from "react-router";


export function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 p-6 text-white">
      <section className="text-center">
        <h1 className="text-4xl font-semibold">
          404
        </h1>

        <p className="mt-3 text-zinc-400">
          Page not found.
        </p>

        <Link
          to="/"
          className="mt-6 inline-block underline"
        >
          Back to Bar Vision
        </Link>
      </section>
    </main>
  );
}
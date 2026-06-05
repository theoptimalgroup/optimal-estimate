"use client";

type GlobalErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 antialiased">
        <main className="flex min-h-screen items-center justify-center px-4">
          <div className="w-full max-w-md space-y-4 rounded-xl border border-red-200 bg-white p-6 shadow-sm">
            <h1 className="text-lg font-semibold">Application error</h1>
            <p className="text-sm text-slate-600">{error.message || "An unexpected error occurred."}</p>
            <button
              type="button"
              onClick={() => reset()}
              className="inline-flex h-9 items-center justify-center rounded-md bg-blue-600 px-4 text-sm font-medium text-white hover:bg-blue-700"
            >
              Try again
            </button>
          </div>
        </main>
      </body>
    </html>
  );
}

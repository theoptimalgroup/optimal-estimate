const API = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";

export default async function globalSetup() {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${API}/health`);
      if (response.ok) {
        return;
      }
    } catch {
      // retry until backend is up
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`Backend not ready at ${API}`);
}

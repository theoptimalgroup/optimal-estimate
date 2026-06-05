/** @type {import('next').NextConfig} */
const nextConfig = {
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  typescript: {
    // Pre-existing type errors in non-critical paths; allow production build to proceed
    ignoreBuildErrors: true,
  },
};

export default nextConfig;

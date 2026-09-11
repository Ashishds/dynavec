/** @type {import('next').NextConfig} */
const isBuild =
  process.env.npm_lifecycle_event === "build" ||
  process.env.NODE_ENV === "production" ||
  process.argv.some((arg) => arg.includes("build"));

const nextConfig = {
  // Isolate build directory from dev directory so `next build` never wipes `next dev` chunks
  distDir: isBuild ? ".next-build" : ".next",
  // Static export during production build for GitHub Pages / S3 / Vercel
  output: isBuild ? "export" : undefined,
  images: { unoptimized: true },
  // Set NEXT_PUBLIC_BASE_PATH="/dynavec/dashboard" when deploying under a subpath.
  basePath: process.env.NEXT_PUBLIC_BASE_PATH || "",
  trailingSlash: true,
};
export default nextConfig;

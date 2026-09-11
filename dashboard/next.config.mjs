/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export during production build for GitHub Pages / S3 / Vercel
  output: process.env.NODE_ENV === "production" ? "export" : undefined,
  images: { unoptimized: true },
  // Set NEXT_PUBLIC_BASE_PATH="/dynavec/dashboard" when deploying under a subpath.
  basePath: process.env.NEXT_PUBLIC_BASE_PATH || "",
  trailingSlash: true,
};
export default nextConfig;

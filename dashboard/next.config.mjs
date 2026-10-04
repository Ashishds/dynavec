const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  // Set NEXT_PUBLIC_BASE_PATH="/dynavec/dashboard" when deploying under a subpath.
  basePath: process.env.NEXT_PUBLIC_BASE_PATH || "",
  trailingSlash: true,
};
export default nextConfig;

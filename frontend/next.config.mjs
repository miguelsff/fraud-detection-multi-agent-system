/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker optimization
  output: "standalone",

  // Disable telemetry in production
  productionBrowserSourceMaps: false,

  // Optimize images
  images: {
    domains: [],
    unoptimized: process.env.NODE_ENV === "development",
  },
};

export default nextConfig;

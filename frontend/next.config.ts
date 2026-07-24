import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  images: { remotePatterns: [] },
  experimental: { cpus: 2 },
};
export default nextConfig;

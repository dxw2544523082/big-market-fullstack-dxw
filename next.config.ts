import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  env: {
    API_HOST_URL: process.env.API_HOST_URL
  },
};

export default nextConfig;

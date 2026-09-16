import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "../.."),
  poweredByHeader: false,
  devIndicators: false,
    transpilePackages: ["@manobal/ui", "@manobal/contracts", "@manobal/i18n", "@manobal/illustrations"],
  env: {
    NEXT_PUBLIC_MANOBAL_MODE: process.env.NEXT_PUBLIC_MANOBAL_MODE ?? "demo",
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "no-referrer" },
          {
            key: "Permissions-Policy",
            value: "camera=(self), microphone=(self), geolocation=()",
          },
          {
            key: "Content-Security-Policy",
            value:
              "default-src 'self'; connect-src 'self' http://localhost:8000 ws://localhost:8000 ws://localhost:8080; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; worker-src 'self' blob:; frame-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'",
          },
        ],
      },
    ];
  },
};

export default nextConfig;

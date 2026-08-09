import type { NextConfig } from "next";

const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "connect-src 'self'",
  "font-src 'self' data:",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "img-src 'self' data: blob:",
  "object-src 'none'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
].join("; ");

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: process.cwd(),
  // Django is not reachable from outside the swarm, so the admin and its assets are
  // proxied through this server. Everything else already goes through the route
  // handlers in app/api/.
  //
  // Next evaluates rewrites() at BUILD time and bakes the destination into the route
  // manifest, so SERVER_API_BASE_URL must be set when `next build` runs -- the
  // Dockerfile passes it as a build argument.
  //
  // The :path* destinations re-append the trailing slash that Next's normalisation
  // strips, because Django's APPEND_SLASH would otherwise redirect straight back and
  // the two would loop.
  async rewrites() {
    const backend =
      process.env.SERVER_API_BASE_URL ??
      process.env.NEXT_PUBLIC_API_BASE_URL ??
      "http://localhost:8000";

    return [
      { source: "/admin", destination: `${backend}/admin/` },
      { source: "/admin/:path*", destination: `${backend}/admin/:path*/` },
      { source: "/django-static/:path*", destination: `${backend}/django-static/:path*` },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Content-Security-Policy",
            value: contentSecurityPolicy,
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;

/** @type {import('next').NextConfig} */
const backendApiUrl = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

const nextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [
      { source: "/dashboard", destination: "/app", permanent: false },
      { source: "/projects", destination: "/app/projects", permanent: false },
      { source: "/templates", destination: "/app/templates", permanent: false },
      { source: "/evidence", destination: "/app/evidence", permanent: false },
      { source: "/reports", destination: "/app/reports", permanent: false },
      { source: "/weekly-reports", destination: "/app/weekly-reports", permanent: false },
      { source: "/usage", destination: "/app/usage", permanent: false },
      { source: "/settings", destination: "/app/settings", permanent: false },
    ];
  },
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendApiUrl}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;

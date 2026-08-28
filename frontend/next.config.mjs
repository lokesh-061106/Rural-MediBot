/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backendUrl =
      process.env.FASTAPI_BACKEND_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : null);
    if (!backendUrl)
      throw new Error("FASTAPI_BACKEND_URL must be configured in production");
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl.replace(/\/$/, "")}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;

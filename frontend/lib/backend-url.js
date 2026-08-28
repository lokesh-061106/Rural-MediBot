export function getBackendUrl() {
  const configuredUrl = process.env.FASTAPI_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;
  if (configuredUrl) return configuredUrl.replace(/\/$/, "");
  if (process.env.NODE_ENV === "production") {
    throw new Error("FASTAPI_BACKEND_URL must be configured in production");
  }
  return "http://127.0.0.1:8000";
}
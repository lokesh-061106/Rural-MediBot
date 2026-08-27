import { jwtVerify } from "jose";

const secretKeyString = process.env.JWT_SECRET_KEY;
if (!secretKeyString || secretKeyString.length < 32 || secretKeyString === "CHANGE_ME_IN_PRODUCTION") {
  const isBuild = process.env.npm_lifecycle_event === "build" || process.env.NEXT_PHASE === "phase-production-build";
  if (process.env.NODE_ENV === "production" && !isBuild) {
    throw new Error("CRITICAL: JWT_SECRET_KEY must be set securely in production.");
  }
}
const SECRET = new TextEncoder().encode(
  secretKeyString || "test_secret_key_that_is_at_least_thirty_two_chars_long"
);

export async function verifyToken(token) {
  try {
    const { payload } = await jwtVerify(token, SECRET);
    return payload;
  } catch (err) {
    console.error("JWT Verification failed:", err.message);
    return null;
  }
}

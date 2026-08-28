import { jwtVerify } from "jose";

const secretKeyString = process.env.JWT_SECRET_KEY;

export async function verifyToken(token) {
  if (!secretKeyString || secretKeyString.length < 32 || secretKeyString === "CHANGE_ME_IN_PRODUCTION") {
    return null;
  }

  const secret = new TextEncoder().encode(secretKeyString);
  try {
    const { payload } = await jwtVerify(token, secret);
    return payload;
  } catch (err) {
    console.error("JWT Verification failed:", err.message);
    return null;
  }
}

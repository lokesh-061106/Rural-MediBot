import { NextResponse } from "next/server";
import { getBackendUrl } from "@/lib/backend-url";

export async function POST(request) {
  try {
    const body = await request.json();

    // In production, you would use an environment variable for the backend URL
    const backendUrl = getBackendUrl();

    const fastapiResponse = await fetch(`${backendUrl}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!fastapiResponse.ok) {
      const errorData = await fastapiResponse.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || "Invalid credentials" },
        { status: fastapiResponse.status },
      );
    }

    const data = await fastapiResponse.json();

    // data contains { access_token, token_type, user }
    const response = NextResponse.json({
      user: data.user,
      token: data.access_token,
    });

    response.cookies.set("medibot_token", data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: "/",
    });

    return response;
  } catch (err) {
    console.error("Login error:", err);
    return NextResponse.json({ error: "Login failed" }, { status: 500 });
  }
}

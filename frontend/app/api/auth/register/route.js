import { NextResponse } from "next/server";
import { getBackendUrl } from "@/lib/backend-url";

export async function POST(request) {
  try {
    const body = await request.json();
    const { name, email, password, role = "patient" } = body;

    if (!name || !email || !password) {
      return NextResponse.json(
        { error: "All fields are required" },
        { status: 400 },
      );
    }

    const backendUrl = getBackendUrl();

    // 1. Register with FastAPI
    const registerResponse = await fetch(`${backendUrl}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name: name,
        email: email,
        password: password,
        role: role,
      }),
    });

    if (!registerResponse.ok) {
      const errorData = await registerResponse.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || "Registration failed" },
        { status: registerResponse.status },
      );
    }

    // 2. Automatically login after registration
    const loginResponse = await fetch(`${backendUrl}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!loginResponse.ok) {
      return NextResponse.json(
        { error: "Registration successful but auto-login failed" },
        { status: 500 },
      );
    }

    const data = await loginResponse.json();

    const response = NextResponse.json({
      user: data.user,
      token: data.access_token,
    });
    response.cookies.set("medibot_token", data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 7,
      path: "/",
    });

    return response;
  } catch (err) {
    console.error("Register error:", err);
    return NextResponse.json({ error: "Registration failed" }, { status: 500 });
  }
}

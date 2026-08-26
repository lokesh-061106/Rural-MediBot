import { NextResponse } from "next/server";

export async function GET(request) {
  try {
    const token = request.cookies.get("medibot_token")?.value;
    if (!token) return NextResponse.json({ user: null }, { status: 401 });

    const backendUrl = process.env.FASTAPI_BACKEND_URL || "http://localhost:8000";
    const fastapiResponse = await fetch(`${backendUrl}/api/auth/me`, {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });

    if (!fastapiResponse.ok) {
      return NextResponse.json({ user: null }, { status: 401 });
    }

    const userData = await fastapiResponse.json();
    return NextResponse.json({ user: userData });
  } catch (err) {
    return NextResponse.json({ user: null }, { status: 500 });
  }
}

export async function DELETE() {
  const response = NextResponse.json({ success: true });
  response.cookies.delete("medibot_token");
  return response;
}

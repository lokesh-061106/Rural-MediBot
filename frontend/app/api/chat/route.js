import { NextResponse } from "next/server";
import { verifyToken } from "@/lib/auth";
import { getBackendUrl } from "@/lib/backend-url";

export async function POST(request) {
  try {
    const token = request.cookies.get("medibot_token")?.value;
    const user = token ? await verifyToken(token) : null;

    const body = await request.json();

    // In production, you would use an environment variable for the backend URL
    const backendUrl = getBackendUrl();

    const fastapiResponse = await fetch(`${backendUrl}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token && user ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        query: body.query || body.message,
        thread_id: user?.sub || user?.id || body.thread_id || "guest",
        language: body.language || "en",
        conversation_id: body.conversation_id || null,
        latitude: body.latitude ?? null,
        longitude: body.longitude ?? null,
      }),
    });

    if (!fastapiResponse.ok) {
      throw new Error(`FastAPI returned ${fastapiResponse.status}`);
    }

    const data = await fastapiResponse.json();
    return NextResponse.json(data); // Forward exact response from FastAPI
  } catch (err) {
    console.error("Chat error:", err);
    return NextResponse.json(
      {
        response:
          "The assistant is temporarily unavailable. Please try again or use offline guidance.",
        sources: [],
        status: "error",
        offline: true,
      },
      { status: 500 },
    );
  }
}

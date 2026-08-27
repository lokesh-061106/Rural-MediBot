import { NextResponse } from "next/server";
import { verifyToken } from "@/lib/auth";

export async function POST(request) {
  try {
    const token = request.cookies.get("medibot_token")?.value;
    if (!token) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    const user = await verifyToken(token);
    if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const body = await request.json();
    
    // In production, you would use an environment variable for the backend URL
    const backendUrl = process.env.FASTAPI_BACKEND_URL || "http://localhost:8000";
    
    const fastapiResponse = await fetch(`${backendUrl}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        query: body.query || body.message,
        thread_id: user.sub || user.id || "default_user_1",
        language: body.language || "en",
        conversation_id: body.conversation_id || null
      }),
    });
    
    if (!fastapiResponse.ok) {
      throw new Error(`FastAPI returned ${fastapiResponse.status}`);
    }
    
    const data = await fastapiResponse.json();
    return NextResponse.json(data); // Forward exact response from FastAPI
  } catch (err) {
    console.error("Chat error:", err);
    return NextResponse.json({
      response: `DEBUG: ${err.message}`,
      sources: [],
      status: "error"
    }, { status: 500 });
  }
}

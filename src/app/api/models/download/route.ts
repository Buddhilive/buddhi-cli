import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/** Proxy download start request to FastAPI backend. */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/api/models/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error("[API Proxy] download start failed:", err);
    return NextResponse.json(
      {
        error: "backend_unreachable",
        message: `Cannot connect to backend server at ${BACKEND_URL}. Is it running?`,
      },
      { status: 502 }
    );
  }
}

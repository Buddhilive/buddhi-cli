import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/** Proxy download cancellation to FastAPI backend. */
export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ downloadId: string }> }
) {
  const { downloadId } = await params;

  try {
    const res = await fetch(
      `${BACKEND_URL}/api/models/download/${downloadId}/cancel`,
      { method: "POST" }
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error("[API Proxy] cancel failed:", err);
    return NextResponse.json(
      {
        error: "backend_unreachable",
        message: `Cannot connect to backend server at ${BACKEND_URL}. Is it running?`,
      },
      { status: 502 }
    );
  }
}

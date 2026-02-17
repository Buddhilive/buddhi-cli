import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/** Proxy library list to FastAPI backend. */
export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/models/library`);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error("[API Proxy] library list failed:", err);
    return NextResponse.json(
      {
        error: "backend_unreachable",
        message: `Cannot connect to backend server at ${BACKEND_URL}. Is it running?`,
      },
      { status: 502 }
    );
  }
}

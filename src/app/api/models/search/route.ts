import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/** Proxy search requests to FastAPI backend. */
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams.toString();

  try {
    const res = await fetch(`${BACKEND_URL}/api/models/search?${searchParams}`);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error("[API Proxy] search failed:", err);
    return NextResponse.json(
      {
        error: "backend_unreachable",
        message: `Cannot connect to backend server at ${BACKEND_URL}. Is it running?`,
      },
      { status: 502 }
    );
  }
}

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/** Proxy repo files listing. Uses query param to avoid path encoding issues with repo IDs. */
export async function GET(request: NextRequest) {
  const repoId = request.nextUrl.searchParams.get("repo_id");
  if (!repoId) {
    return NextResponse.json(
      { error: "bad_request", message: "repo_id query parameter is required" },
      { status: 400 }
    );
  }

  try {
    const res = await fetch(`${BACKEND_URL}/api/models/${repoId}/files`);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error("[API Proxy] files failed:", err);
    return NextResponse.json(
      {
        error: "backend_unreachable",
        message: `Cannot connect to backend server at ${BACKEND_URL}. Is it running?`,
      },
      { status: 502 }
    );
  }
}

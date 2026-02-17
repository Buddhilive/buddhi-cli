import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/** Proxy model deletion to FastAPI backend. */
export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ modelId: string }> }
) {
  const { modelId } = await params;

  try {
    const res = await fetch(`${BACKEND_URL}/api/models/library/${modelId}`, {
      method: "DELETE",
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error("[API Proxy] delete model failed:", err);
    return NextResponse.json(
      {
        error: "backend_unreachable",
        message: `Cannot connect to backend server at ${BACKEND_URL}. Is it running?`,
      },
      { status: 502 }
    );
  }
}

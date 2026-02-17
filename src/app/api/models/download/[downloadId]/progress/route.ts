import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/**
 * Proxy SSE progress stream from FastAPI to the browser.
 * Pipes the backend response body directly through with text/event-stream headers.
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ downloadId: string }> }
) {
  const { downloadId } = await params;

  try {
    const backendRes = await fetch(
      `${BACKEND_URL}/api/models/download/${downloadId}/progress`,
      { headers: { Accept: "text/event-stream" } }
    );

    if (!backendRes.ok || !backendRes.body) {
      return new Response(
        JSON.stringify({ error: "Failed to connect to progress stream" }),
        {
          status: backendRes.status,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    return new Response(backendRes.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (err) {
    console.error("[API Proxy] SSE progress failed:", err);
    return new Response(
      JSON.stringify({
        error: "backend_unreachable",
        message: `Cannot connect to backend server at ${BACKEND_URL}. Is it running?`,
      }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }
}

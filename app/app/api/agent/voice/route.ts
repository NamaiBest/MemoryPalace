import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const audio = await request.arrayBuffer();
    if (!audio.byteLength) {
      return NextResponse.json({ error: "Voice recording was empty" }, { status: 400 });
    }
    const params = new URLSearchParams();
    const date = request.nextUrl.searchParams.get("date");
    if (date) params.set("date", date);
    const history = request.headers.get("x-memory-history");
    const response = await backendFetch(`/agent/voice?${params.toString()}`, {
      method: "POST",
      headers: {
        "Content-Type": request.headers.get("content-type") ?? "audio/webm",
        ...(history ? { "X-Memory-History": history } : {}),
      },
      body: audio,
    });
    const result = await response.json();
    return NextResponse.json(result, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "Memory Guard voice mode is offline" },
      { status: 503 },
    );
  }
}

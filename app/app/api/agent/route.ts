import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export async function GET() {
  try {
    const response = await backendFetch("/status");
    if (!response.ok) throw new Error(`backend returned ${response.status}`);
    const body = await response.json();
    return NextResponse.json({
      agent: body.agent,
      elastic: body.elastic,
      voice: body.voice,
    });
  } catch {
    return NextResponse.json({ offline: true }, { status: 503 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const response = await backendFetch("/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: body.question,
        date: body.date,
        history: body.history,
      }),
    });
    const result = await response.json();
    return NextResponse.json(result, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "Memory Guard is offline" },
      { status: 503 },
    );
  }
}

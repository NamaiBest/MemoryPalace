import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export const dynamic = "force-dynamic";
// The recap reads every moment in the day rather than a retrieved handful, so it runs
// longer than a chat turn and needs the route to outlive the default budget.
export const maxDuration = 300;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const response = await backendFetch("/agent/recap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: body.date ?? null }),
    });
    const result = await response.json();
    return NextResponse.json(result, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "Memory Guard could not write the recap" },
      { status: 503 },
    );
  }
}

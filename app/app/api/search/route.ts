import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q")?.trim() ?? "";
  const params = new URLSearchParams({ q: query, limit: "30" });
  const eventType = request.nextUrl.searchParams.get("event_type");
  const minimum = request.nextUrl.searchParams.get("min_intensity")
    ?? request.nextUrl.searchParams.get("min_confidence");
  const maximum = request.nextUrl.searchParams.get("max_intensity")
    ?? request.nextUrl.searchParams.get("max_confidence");
  if (eventType) params.set("event_type", eventType);
  if (minimum) params.set("min_intensity", minimum);
  if (maximum) params.set("max_intensity", maximum);
  for (const name of ["date_from", "date_to", "session_id", "user_id", "sort"]) {
    const value = request.nextUrl.searchParams.get(name);
    if (value) params.set(name, value);
  }

  try {
    const response = await backendFetch(`/search?${params.toString()}`);
    const body = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { moments: [], error: body.error ?? `backend returned ${response.status}` },
        { status: response.status === 400 ? 400 : 503 },
      );
    }
    return NextResponse.json(body);
  } catch {
    return NextResponse.json(
      { moments: [], error: "Memory search is offline" },
      { status: 503 },
    );
  }
}

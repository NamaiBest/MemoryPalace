import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export const dynamic = "force-dynamic";

// Stored media is named <32 hex>.<ext> by the backend. Anything else is refused here
// rather than forwarded, so a crafted name can never reach the filesystem.
const NAME = /^[0-9a-f]{32}\.(mp4|mov|jpg|png)$/;

/**
 * Serves stored media with byte-range support.
 *
 * Range handling is not optional for video: a browser <video> element issues a ranged
 * request, and a server that answers 200 with no Content-Length leaves the player unable
 * to seek or even determine duration, so it stalls and retries indefinitely.
 *
 * Clips are a few hundred KB up to a few MB and are buffered whole to slice from. That is
 * fine at this size and keeps the logic simple; streaming ranges straight through would be
 * required if recordings ever grew to hundreds of megabytes.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  if (!NAME.test(name)) {
    return NextResponse.json({ error: "bad media name" }, { status: 400 });
  }

  let body: ArrayBuffer;
  let contentType: string;
  try {
    const upstream = await backendFetch(`/media/${name}`);
    if (!upstream.ok) {
      return NextResponse.json({ error: "not found" }, { status: 404 });
    }
    body = await upstream.arrayBuffer();
    contentType = upstream.headers.get("Content-Type") ?? "application/octet-stream";
  } catch {
    return NextResponse.json({ error: "backend unavailable" }, { status: 503 });
  }

  const total = body.byteLength;
  const common = {
    "Content-Type": contentType,
    "Accept-Ranges": "bytes",
    "Cache-Control": "private, max-age=3600",
  };

  const range = request.headers.get("range");
  const match = range?.match(/^bytes=(\d*)-(\d*)$/);
  if (match) {
    const [, rawStart, rawEnd] = match;
    // "bytes=-500" means the last 500 bytes, not a range starting at zero.
    const start = rawStart ? Number(rawStart) : Math.max(0, total - Number(rawEnd || 0));
    const end = rawStart
      ? Math.min(rawEnd ? Number(rawEnd) : total - 1, total - 1)
      : total - 1;

    if (Number.isNaN(start) || start > end || start >= total) {
      return new NextResponse(null, {
        status: 416,
        headers: { ...common, "Content-Range": `bytes */${total}` },
      });
    }

    const slice = body.slice(start, end + 1);
    return new NextResponse(slice, {
      status: 206,
      headers: {
        ...common,
        "Content-Range": `bytes ${start}-${end}/${total}`,
        "Content-Length": String(slice.byteLength),
      },
    });
  }

  return new NextResponse(body, {
    status: 200,
    headers: { ...common, "Content-Length": String(total) },
  });
}

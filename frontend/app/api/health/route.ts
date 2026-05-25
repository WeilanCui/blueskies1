import { NextResponse } from "next/server";

export async function GET() {
  const baseUrl = process.env.SERVER_API_BASE_URL ?? "http://backend:8000";
  const response = await fetch(`${baseUrl}/api/health/`, {
    cache: "no-store",
  });

  if (!response.ok) {
    return NextResponse.json(
      { status: "error", upstreamStatus: response.status },
      { status: 502 },
    );
  }

  const data = await response.json();
  return NextResponse.json(data);
}

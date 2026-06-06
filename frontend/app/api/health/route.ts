import { NextResponse } from "next/server";

import { getServerApiBaseUrl } from "../../../lib/apiBaseUrl";

export async function GET() {
  const baseUrl = getServerApiBaseUrl();
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

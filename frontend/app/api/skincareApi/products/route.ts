import { NextRequest, NextResponse } from "next/server";

import { getServerApiBaseUrl } from "../../../../lib/apiBaseUrl";

export async function GET() {
  const baseUrl = getServerApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/skincare/products/`, {
    cache: "no-store",
  });

  const data = await response.json().catch(() => ({}));
  return NextResponse.json(data, { status: response.status });
}

export async function POST(request: NextRequest) {
  const baseUrl = getServerApiBaseUrl();
  const body = await request.json();

  const response = await fetch(`${baseUrl}/api/skincare/products/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  const data = await response.json().catch(() => ({}));
  return NextResponse.json(data, { status: response.status });
}

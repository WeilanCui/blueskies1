import { NextRequest, NextResponse } from "next/server";

import { getServerApiBaseUrl } from "../../../../../lib/apiBaseUrl";

export async function GET(request: NextRequest) {
  const baseUrl = getServerApiBaseUrl();
  const search = request.nextUrl.searchParams.toString();
  const suffix = search ? `?${search}` : "";

  const response = await fetch(`${baseUrl}/api/skincare/products/search/${suffix}`, {
    cache: "no-store",
  });

  const data = await response.json().catch(() => ({}));
  return NextResponse.json(data, { status: response.status });
}

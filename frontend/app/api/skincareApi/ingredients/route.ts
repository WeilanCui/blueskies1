import { NextResponse } from "next/server";

import { getServerApiBaseUrl } from "../../../../lib/apiBaseUrl";

export async function GET() {
  const baseUrl = getServerApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/skincare/ingredients/`, {
    cache: "no-store",
  });

  const data = await response.json().catch(() => ({}));
  return NextResponse.json(data, { status: response.status });
}

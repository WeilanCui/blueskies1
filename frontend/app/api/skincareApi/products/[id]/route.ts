import { NextResponse } from "next/server";

import { getServerApiBaseUrl } from "../../../../../lib/apiBaseUrl";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_request: Request, context: RouteContext) {
  const { id } = await context.params;
  const baseUrl = getServerApiBaseUrl();

  const response = await fetch(`${baseUrl}/api/skincare/products/${id}/`, {
    cache: "no-store",
  });

  const data = await response.json().catch(() => ({}));
  return NextResponse.json(data, { status: response.status });
}

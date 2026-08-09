import type { NextRequest } from "next/server";

import { proxyBackendJson } from "../../../../lib/backendProxy";

export async function GET(request: NextRequest) {
  const search = request.nextUrl.searchParams.toString();
  const suffix = search ? `?${search}` : "";
  return proxyBackendJson(request, `/api/skin-concerns/search/${suffix}`);
}

import { proxyBackendJson } from "../../../lib/backendProxy";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const query = url.searchParams.toString();
  const path = query ? `/api/daily-checkins/?${query}` : "/api/daily-checkins/";
  return proxyBackendJson(request, path);
}

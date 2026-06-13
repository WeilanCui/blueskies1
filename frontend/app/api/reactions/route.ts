import { proxyBackendJson } from "../../../lib/backendProxy";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const query = url.searchParams.toString();
  const path = query ? `/api/reactions/?${query}` : "/api/reactions/";
  return proxyBackendJson(request, path);
}

export async function POST(request: Request) {
  const body = await request.json();
  return proxyBackendJson(request, "/api/reactions/", { body });
}

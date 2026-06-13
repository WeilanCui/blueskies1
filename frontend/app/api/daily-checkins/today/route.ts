import { proxyBackendJson } from "../../../../lib/backendProxy";

export async function GET(request: Request) {
  return proxyBackendJson(request, "/api/daily-checkins/today/");
}

export async function POST(request: Request) {
  const body = await request.json();
  return proxyBackendJson(request, "/api/daily-checkins/today/", { body });
}

export async function PUT(request: Request) {
  const body = await request.json();
  return proxyBackendJson(request, "/api/daily-checkins/today/", { body });
}

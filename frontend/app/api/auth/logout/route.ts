import { proxyBackendJson } from "../../../../lib/backendProxy";

export async function POST(request: Request) {
  return proxyBackendJson(request, "/api/auth/logout/");
}

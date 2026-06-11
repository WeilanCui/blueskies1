import { proxyBackendJson } from "../../../../lib/backendProxy";

export async function GET(request: Request) {
  return proxyBackendJson(request, "/api/auth/me/");
}

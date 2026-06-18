import { proxyBackendJson } from "../../../../lib/backendProxy";

export async function GET(request: Request) {
  return proxyBackendJson(request, "/api/auth/me/");
}

export async function PATCH(request: Request) {
  const body = await request.json();
  return proxyBackendJson(request, "/api/auth/me/", { body, method: "PATCH" });
}

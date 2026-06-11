import { proxyBackendJson } from "../../../../lib/backendProxy";

export async function POST(request: Request) {
  const body = await request.json();
  return proxyBackendJson(request, "/api/auth/signup/", { body });
}

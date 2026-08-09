import { proxyBackendJson } from "../../../../../lib/backendProxy";

export async function GET(request: Request) {
  const query = new URL(request.url).searchParams.toString();
  return proxyBackendJson(
    request,
    `/api/products/search/${query ? `?${query}` : ""}`,
  );
}

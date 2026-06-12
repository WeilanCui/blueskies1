import { proxyBackendJson } from "../../../../lib/backendProxy";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(request: Request, context: RouteContext) {
  const { id } = await context.params;
  return proxyBackendJson(request, `/api/products/${encodeURIComponent(id)}/`);
}

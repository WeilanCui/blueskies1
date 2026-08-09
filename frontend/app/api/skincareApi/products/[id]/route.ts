import { proxyBackendJson } from "../../../../../lib/backendProxy";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(request: Request, context: RouteContext) {
  const { id } = await context.params;
  // The catalog id is a slug for seeded rows and a pk for everything else, so
  // it is not always URL-safe on its own.
  return proxyBackendJson(request, `/api/products/${encodeURIComponent(id)}/`);
}

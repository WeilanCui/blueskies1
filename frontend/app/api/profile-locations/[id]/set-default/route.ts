import { proxyBackendJson } from "../../../../../lib/backendProxy";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function POST(request: Request, context: RouteContext) {
  const { id } = await context.params;
  return proxyBackendJson(
    request,
    `/api/profile-locations/${encodeURIComponent(id)}/set-default/`,
  );
}

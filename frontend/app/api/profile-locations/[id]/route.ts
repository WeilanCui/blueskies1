import { proxyBackendJson } from "../../../../lib/backendProxy";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(request: Request, context: RouteContext) {
  const { id } = await context.params;
  return proxyBackendJson(
    request,
    `/api/profile-locations/${encodeURIComponent(id)}/`,
  );
}

export async function PUT(request: Request, context: RouteContext) {
  const { id } = await context.params;
  const body = await request.json();
  return proxyBackendJson(
    request,
    `/api/profile-locations/${encodeURIComponent(id)}/`,
    {
      body,
    },
  );
}

export async function PATCH(request: Request, context: RouteContext) {
  const { id } = await context.params;
  const body = await request.json();
  return proxyBackendJson(
    request,
    `/api/profile-locations/${encodeURIComponent(id)}/`,
    {
      method: "PATCH",
      body,
    },
  );
}

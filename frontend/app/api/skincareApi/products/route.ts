import { NextResponse } from "next/server";

import { proxyBackendJson } from "../../../../lib/backendProxy";

export async function GET(request: Request) {
  const query = new URL(request.url).searchParams.toString();
  return proxyBackendJson(
    request,
    `/api/products/search/${query ? `?${query}` : ""}`,
  );
}

type CreateBody = {
  brand?: string;
  name?: string;
  ingredients?: string;
};

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as CreateBody;

  // The catalog's "add product" form is the formulation submit endpoint wearing
  // different field names: brand/name/ingredients -> brand/name/formulation.
  const submitted = await proxyBackendJson(
    request,
    "/api/formulations/submit/",
    {
      method: "POST",
      body: {
        name: body.name ?? "",
        brand: body.brand ?? "",
        formulation: body.ingredients ?? "",
      },
    },
  );

  if (!submitted.ok) {
    return submitted;
  }

  // Submit answers with the formulation it ingested, but the catalog list and
  // detail views speak the product shape, so read the owning product back.
  const created = (await submitted.json()) as {
    formulation?: { product_id?: number | null };
  };
  const productId = created.formulation?.product_id;

  if (productId === undefined || productId === null) {
    return NextResponse.json(
      { detail: "The product was created but could not be read back." },
      { status: 502 },
    );
  }

  return proxyBackendJson(request, `/api/products/${productId}/`, {
    method: "GET",
  });
}

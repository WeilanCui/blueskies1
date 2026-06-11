import { NextResponse } from "next/server";

import { getServerApiBaseUrl } from "../../../lib/apiBaseUrl";

export async function POST(request: Request) {
  const baseUrl = getServerApiBaseUrl();

  try {
    const body = await request.json();
    const response = await fetch(`${baseUrl}/api/contact/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      { detail: "Could not reach the backend API." },
      { status: 502 },
    );
  }
}

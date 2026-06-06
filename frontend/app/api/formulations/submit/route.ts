import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const baseUrl = process.env.SERVER_API_BASE_URL ?? "http://backend:8000";

  try {
    const body = await request.json();
    const response = await fetch(`${baseUrl}/api/formulations/submit/`, {
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

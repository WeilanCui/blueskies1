import { NextResponse } from "next/server";

import { getServerApiBaseUrl } from "./apiBaseUrl";

type ProxyOptions = {
  method?: string;
  body?: unknown;
};

function appendSetCookies(response: NextResponse, backendResponse: Response) {
  const headers = backendResponse.headers as Headers & {
    getSetCookie?: () => string[];
  };
  const setCookies = headers.getSetCookie?.() ?? [];
  const fallbackCookie = setCookies.length === 0 ? headers.get("set-cookie") : null;

  for (const cookie of setCookies) {
    response.headers.append("set-cookie", cookie);
  }
  if (fallbackCookie) {
    response.headers.append("set-cookie", fallbackCookie);
  }
}

export async function proxyBackendJson(
  request: Request,
  path: string,
  { method = request.method, body }: ProxyOptions = {},
) {
  const baseUrl = getServerApiBaseUrl();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const cookie = request.headers.get("cookie");
  if (cookie) {
    headers.Cookie = cookie;
  }

  try {
    const backendResponse = await fetch(`${baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
    const data = await backendResponse.json();
    const response = NextResponse.json(data, { status: backendResponse.status });
    appendSetCookies(response, backendResponse);
    return response;
  } catch {
    return NextResponse.json(
      { detail: "Could not reach the backend API." },
      { status: 502 },
    );
  }
}

/** Server-side Django API base URL (SSR and route handlers). */
export function getServerApiBaseUrl(): string {
  return (
    process.env.SERVER_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000"
  );
}

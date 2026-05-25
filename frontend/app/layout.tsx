import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Blueskies",
  description: "Django, Celery, Postgres, Redis, and Next.js starter",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

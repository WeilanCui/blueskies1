import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Blueskies",
  description:
    "Personalized skincare intelligence for skin tracking, regimen analysis, and ingredient science.",
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

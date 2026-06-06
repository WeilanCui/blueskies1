import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Blueskies",
  description: "Personalized skincare intelligence with ingredient research",
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

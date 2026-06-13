import type { Metadata } from "next";
import "./globals.css";
import { AppFrame } from "../components/AppFrame";
import Providers from "./providers";

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
    <html className="light" data-theme="light" lang="en">
      <body>
        <Providers>
          <AppFrame>{children}</AppFrame>
        </Providers>
      </body>
    </html>
  );
}

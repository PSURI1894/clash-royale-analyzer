import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Clash Royale Helper",
  description: "Deterministic deck analyzer — deck maker, analyzer & (soon) battle simulator.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

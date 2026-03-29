import type { Metadata } from "next";
import { Source_Serif_4, Space_Grotesk } from "next/font/google";

import "./globals.css";

const headingFont = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});

const bodyFont = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-source-serif",
});

export const metadata: Metadata = {
  title: "Adaptive Quiz Platform",
  description: "Collect quiz interaction data for active learning experiments.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${headingFont.variable} ${bodyFont.variable}`}>{children}</body>
    </html>
  );
}


import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GradLens — semantic search for graduate schemes",
  description:
    "Find entry-level engineering roles, internships, and graduate schemes with natural-language queries. Built by a final-year CS student, for final-year students.",
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

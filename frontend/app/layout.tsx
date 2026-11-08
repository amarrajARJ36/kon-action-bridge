import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KON Commerce Demo | Governed Conversational AI Shopping Assistant",
  description:
    "Mock grocery catalogue demonstrating how an enterprise conversational agent could interact with a retailer's commerce APIs through a governed tool layer.",
  keywords: ["KON", "conversational commerce", "AI governance", "policy engine", "enterprise AI", "shopping assistant"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased font-sans bg-[#f4f6f8] text-[#111827]">{children}</body>
    </html>
  );
}

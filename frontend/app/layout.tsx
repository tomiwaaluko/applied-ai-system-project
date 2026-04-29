import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "CareerScope AI",
  description: "Multi-agent AI career intelligence dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-[radial-gradient(circle_at_top_left,#064e3b_0,#09090b_42%,#030712_100%)] text-zinc-100">
        <nav className="border-b border-white/10 bg-black/20 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="text-lg font-semibold tracking-tight text-white">
              CareerScope
            </Link>
            <div className="flex gap-5 text-sm text-zinc-300">
              <Link href="/" className="hover:text-white">Analyze</Link>
              <Link href="/reports" className="hover:text-white">Reports</Link>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}

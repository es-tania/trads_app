import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import { Sidebar } from "@/components/Sidebar";
import "./globals.css";

const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-display" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "Trads App",
  description: "Studio de localisation : scraping, traduction, sous-titres.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${display.variable} ${mono.variable}`}>
      <body className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 px-8 py-10">
          <div className="mx-auto max-w-2xl">{children}</div>
        </main>
      </body>
    </html>
  );
}

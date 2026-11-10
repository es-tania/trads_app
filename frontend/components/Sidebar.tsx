"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS: { href: string; label: string; disabled?: boolean }[] = [
  { href: "/", label: "Accueil" },
  { href: "/scraping", label: "Scraping & traduction" },
  { href: "/translate", label: "Traduire un .docx" },
  { href: "/subtitles", label: "Sous-titres vidéo" },
  { href: "/ocr", label: "OCR image" },
  { href: "/history", label: "Historique" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 shrink-0 border-r border-border bg-surface px-4 py-6">
      <div className="mb-8 px-2">
        <p className="font-display text-lg tracking-tight">LADS App</p>
        <p className="text-xs text-dim">Studio de localisation</p>
      </div>
      <nav className="space-y-1">
        {LINKS.map((link) => {
          const active = pathname === link.href;
          if (link.disabled) {
            return (
              <span
                key={link.href}
                className="flex cursor-not-allowed items-center justify-between rounded-md px-3 py-2 text-sm text-dim/50"
                title="Pas encore branché — voir la Phase 5 de la roadmap"
              >
                {link.label}
                <span className="text-[10px] uppercase tracking-wide">Bientôt</span>
              </span>
            );
          }
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`block rounded-md px-3 py-2 text-sm transition-colors ${
                active ? "bg-accent-soft text-ink" : "text-dim hover:bg-surface2 hover:text-ink"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

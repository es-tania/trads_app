import Link from "next/link";

const MODULES = [
  {
    href: "/scraping",
    title: "Scraping & traduction",
    text: "Récupère un script depuis une URL de wiki, traduis-le, génère les .docx EN et FR.",
  },
  {
    href: "/translate",
    title: "Traduire un .docx",
    text: "Upload un .docx en anglais, récupère sa traduction française.",
  },
  {
    href: "/subtitles",
    title: "Sous-titres vidéo",
    text: "Depuis un lien YouTube (ou une vidéo uploadée) et des .docx EN/FR, génère un .srt synchronisé.",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl">Studio de localisation</h1>
        <p className="mt-2 text-dim">Choisis un module pour commencer.</p>
      </div>

      <div className="space-y-3">
        {MODULES.map((m) => (
          <Link
            key={m.href}
            href={m.href}
            className="block rounded-lg border border-border bg-surface p-5 transition-colors hover:border-accent/50"
          >
            <p className="font-medium">{m.title}</p>
            <p className="mt-1 text-sm text-dim">{m.text}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

"use client";

import { TranslateEngine } from "@/lib/api";

interface Props {
  value: TranslateEngine;
  onChange: (engine: TranslateEngine) => void;
}

const OPTIONS: { value: TranslateEngine; label: string; hint: string }[] = [
  { value: "deepl", label: "DeepL (API officielle)", hint: "clé requise, palier gratuit 500k car./mois" },
  { value: "deeplx", label: "DeepLX (local)", hint: "gratuit, sans clé, nécessite Node.js (CLI installé côté backend)" },
];

/** Choix du moteur de traduction, partagé entre la page /translate et /scraping. */
export function EngineSelector({ value, onChange }: Props) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium text-dim">Moteur de traduction</legend>
      <div className="flex flex-wrap gap-3">
        {OPTIONS.map((opt) => (
          <label
            key={opt.value}
            className={`flex cursor-pointer flex-col rounded-md border px-3 py-2 text-sm transition-colors ${
              value === opt.value ? "border-accent bg-accent/10" : "border-border hover:border-accent/50"
            }`}
          >
            <span className="flex items-center gap-2">
              <input
                type="radio"
                name="translate-engine"
                value={opt.value}
                checked={value === opt.value}
                onChange={() => onChange(opt.value)}
                className="accent-accent"
              />
              {opt.label}
            </span>
            <span className="mt-0.5 pl-5 text-xs text-dim/70">{opt.hint}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

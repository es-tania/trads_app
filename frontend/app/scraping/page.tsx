"use client";

import { useState } from "react";
import {
  generateScrapedDocx,
  scrapeUrl,
  scrapingDownloadUrl,
  translateScrapedScript,
  JobState,
  TranslateEngine,
} from "@/lib/api";
import { JobStatusPanel } from "@/components/JobStatusPanel";
import { EngineSelector } from "@/components/EngineSelector";

export default function ScrapingPage() {
  const [url, setUrl] = useState("");
  const [engine, setEngine] = useState<TranslateEngine>("deeplx");
  const [scrapeJobId, setScrapeJobId] = useState<string | null>(null);
  const [translateJobId, setTranslateJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleScrape(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setError(null);
    setTranslateJobId(null);
    try {
      const { job_id } = await scrapeUrl(url.trim());
      setScrapeJobId(job_id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleTranslate(folder: string, filename: string) {
    setError(null);
    try {
      const { job_id } = await translateScrapedScript(folder, filename, engine);
      setTranslateJobId(job_id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl">Scraping & traduction</h1>
        <p className="mt-2 text-dim">Colle le lien d'une page de script du wiki.</p>
      </div>

      <form onSubmit={handleScrape} className="flex gap-2">
        <input
          type="url"
          placeholder="https://..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="flex-1 rounded-md border border-border bg-surface px-3 py-2 text-sm placeholder:text-dim/50"
        />
        <button type="submit" className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white">
          Récupérer
        </button>
      </form>
      {error && <p className="text-sm text-danger">{error}</p>}

      {scrapeJobId && (
        <Section title="1. Récupération du script">
          <JobStatusPanel
            jobId={scrapeJobId}
            renderDone={(job) => (
              <DocxActions
                job={job}
                lang="EN"
                onTranslate={!translateJobId ? () => handleTranslate(job.folder as string, job.file as string) : undefined}
              />
            )}
          />
        </Section>
      )}

      {translateJobId && (
        <Section title="2. Traduction FR">
          <JobStatusPanel jobId={translateJobId} renderDone={(job) => <DocxActions job={job} lang="FR" />} />
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3 border-t border-border pt-6">
      <p className="text-sm font-medium text-dim">{title}</p>
      {children}
    </div>
  );
}

/** Actions disponibles une fois un job (scrape ou traduction) terminé : générer/télécharger le docx. */
function DocxActions({
  job,
  lang,
  onTranslate,
}: {
  job: JobState;
  lang: "EN" | "FR";
  onTranslate?: () => void;
}) {
  const [docx, setDocx] = useState<{ folder: string; file: string } | null>(null);
  const [generating, setGenerating] = useState(false);
  const folder = job.folder as string;
  const filename = job.file as string;

  async function handleGenerateDocx() {
    setGenerating(true);
    try {
      const result = await generateScrapedDocx(folder, filename, lang);
      setDocx(result);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      {job.title && <span className="text-dim">« {job.title as string} »</span>}
      <a
        href={scrapingDownloadUrl(folder, filename)}
        className="rounded-md border border-border px-3 py-1.5 hover:border-accent/50"
      >
        Télécharger le .json
      </a>
      {docx ? (
        <a
          href={scrapingDownloadUrl(docx.folder, docx.file)}
          className="rounded-md bg-accent px-3 py-1.5 font-medium text-white"
        >
          Télécharger {docx.file}
        </a>
      ) : (
        <button
          onClick={handleGenerateDocx}
          disabled={generating}
          className="rounded-md border border-border px-3 py-1.5 hover:border-accent/50 disabled:opacity-40"
        >
          {generating ? "Génération…" : `Générer le .docx ${lang}`}
        </button>
      )}
      {onTranslate && (
        <button onClick={onTranslate} className="rounded-md border border-border px-3 py-1.5 hover:border-accent/50">
          Traduire en FR
        </button>
      )}
    </div>
  );
}

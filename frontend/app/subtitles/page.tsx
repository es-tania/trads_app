"use client";

import { useState } from "react";
import { generateSubtitles, subtitlesVideoUrl } from "@/lib/api";
import { JobStatusPanel } from "@/components/JobStatusPanel";

export default function SubtitlesPage() {
  const [source, setSource] = useState<"youtube" | "upload">("youtube");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [video, setVideo] = useState<File | null>(null);
  const [enDocx, setEnDocx] = useState<File | null>(null);
  const [frDocx, setFrDocx] = useState<File | null>(null);
  const [whisperModel, setWhisperModel] = useState("medium");
  const [minDuration, setMinDuration] = useState(1.2);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = enDocx && frDocx && (source === "youtube" ? youtubeUrl.trim() : video);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!enDocx || !frDocx) return;
    setError(null);
    try {
      const { job_id } = await generateSubtitles({
        enDocx,
        frDocx,
        youtubeUrl: source === "youtube" ? youtubeUrl.trim() : undefined,
        video: source === "upload" ? video ?? undefined : undefined,
        whisperModel,
        minDuration,
      });
      setJobId(job_id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl">Sous-titres vidéo</h1>
        <p className="mt-2 text-dim">
          Aligne un .docx EN/FR sur une vidéo pour générer un .srt synchronisé. Peut prendre
          plusieurs minutes (Whisper) — suis la progression ci-dessous.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="flex gap-2">
          {(["youtube", "upload"] as const).map((s) => (
            <button
              type="button"
              key={s}
              onClick={() => setSource(s)}
              className={`rounded-md border px-3 py-1.5 text-sm ${
                source === s ? "border-accent bg-accent-soft" : "border-border text-dim"
              }`}
            >
              {s === "youtube" ? "Lien YouTube" : "Uploader la vidéo"}
            </button>
          ))}
        </div>

        {source === "youtube" ? (
          <input
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
            className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm placeholder:text-dim/50"
          />
        ) : (
          <FileField label="Vidéo" accept="video/*" onChange={setVideo} value={video} />
        )}

        <div className="grid grid-cols-2 gap-4">
          <FileField label=".docx EN" accept=".docx" onChange={setEnDocx} value={enDocx} />
          <FileField label=".docx FR" accept=".docx" onChange={setFrDocx} value={frDocx} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <label className="text-sm text-dim">
            Modèle Whisper
            <select
              value={whisperModel}
              onChange={(e) => setWhisperModel(e.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
            >
              <option value="small">small (rapide)</option>
              <option value="medium">medium (recommandé)</option>
              <option value="large-v3">large-v3 (précis, plus lent)</option>
            </select>
          </label>
          <label className="text-sm text-dim">
            Durée min. par ligne (s)
            <input
              type="number"
              step="0.1"
              value={minDuration}
              onChange={(e) => setMinDuration(Number(e.target.value))}
              className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink"
            />
          </label>
        </div>

        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Générer les sous-titres
        </button>
        {error && <p className="text-sm text-danger">{error}</p>}
      </form>

      {jobId && (
        <JobStatusPanel
          jobId={jobId}
          renderDone={() =>
            source === "youtube" ? (
              <a
                href={subtitlesVideoUrl(jobId)}
                className="rounded-md border border-border px-3 py-1.5 text-sm hover:border-accent/50"
              >
                Télécharger la vidéo
              </a>
            ) : undefined
          }
        />
      )}
    </div>
  );
}

function FileField({
  label,
  accept,
  value,
  onChange,
}: {
  label: string;
  accept: string;
  value: File | null;
  onChange: (f: File | null) => void;
}) {
  return (
    <label className="block rounded-md border border-dashed border-border bg-surface p-3 text-center text-xs text-dim hover:border-accent/50">
      <input
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
      <span className="block text-dim/70">{label}</span>
      <span className="mt-1 block truncate">{value ? value.name : "Choisir un fichier"}</span>
    </label>
  );
}

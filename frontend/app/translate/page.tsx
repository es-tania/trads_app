"use client";

import { useState } from "react";
import { translateDocx } from "@/lib/api";
import { JobStatusPanel } from "@/components/JobStatusPanel";

export default function TranslatePage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError(null);
    try {
      const { job_id } = await translateDocx(file);
      setJobId(job_id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl">Traduire un .docx</h1>
        <p className="mt-2 text-dim">Upload un document en anglais, reçois sa traduction française.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block rounded-lg border border-dashed border-border bg-surface p-6 text-center text-sm text-dim hover:border-accent/50">
          <input
            type="file"
            accept=".docx"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          {file ? file.name : "Cliquer pour choisir un fichier .docx"}
        </label>

        <button
          type="submit"
          disabled={!file}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Traduire
        </button>
        {error && <p className="text-sm text-danger">{error}</p>}
      </form>

      {jobId && <JobStatusPanel jobId={jobId} />}
    </div>
  );
}

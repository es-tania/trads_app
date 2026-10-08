"use client";

import { useEffect, useRef, useState } from "react";
import { useJob } from "@/lib/useJob";
import { cancelJob, jobResultUrl, JobState } from "@/lib/api";
import { StatusPill } from "./StatusPill";

interface Props {
  jobId: string;
  /** Contenu personnalisé affiché une fois le job terminé (ex: boutons d'étape suivante). */
  renderDone?: (job: JobState) => React.ReactNode;
}

export function JobStatusPanel({ jobId, renderDone }: Props) {
  const job = useJob(jobId);
  const logRef = useRef<HTMLDivElement>(null);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [job?.logs.length]);

  useEffect(() => {
    // Le statut a bougé (ex: passé à "cancelled") : on peut réactiver le bouton
    // si jamais l'utilisateur relance quelque chose plus tard.
    if (job?.status !== "queued" && job?.status !== "running") setCancelling(false);
  }, [job?.status]);

  if (!job) return null;

  const isActive = job.status === "queued" || job.status === "running";

  async function handleCancel() {
    setCancelling(true);
    try {
      await cancelJob(jobId);
    } catch {
      setCancelling(false); // le polling reflètera de toute façon l'état réel
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <StatusPill status={job.status} />
        <div className="flex items-center gap-3">
          {job.status === "error" && job.message && (
            <span className="text-sm text-danger">{job.message}</span>
          )}
          {isActive && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="rounded-md border border-danger/40 px-3 py-1 text-xs text-danger hover:bg-danger/10 disabled:opacity-40"
            >
              {cancelling ? "Arrêt demandé…" : "Arrêter"}
            </button>
          )}
        </div>
      </div>

      <div ref={logRef} className="log-console h-56 overflow-y-auto p-3">
        {job.logs.length === 0 ? (
          <p className="text-dim/60">En attente des premières lignes de log…</p>
        ) : (
          job.logs.map((line, i) => <div key={i}>{line}</div>)
        )}
      </div>

      {job.status === "done" && (
        <div className="flex flex-wrap items-center gap-3">
          {job.result_filename && (
            <a
              href={jobResultUrl(job.job_id)}
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90"
            >
              Télécharger {job.result_filename}
            </a>
          )}
          {renderDone?.(job)}
        </div>
      )}
    </div>
  );
}

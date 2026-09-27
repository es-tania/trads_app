"use client";

import { useEffect, useState } from "react";
import { getJobStatus, JobState, WS_BASE } from "./api";

export function useJob(jobId: string | null) {
  const [state, setState] = useState<JobState | null>(null);

  useEffect(() => {
    if (!jobId) {
      setState(null);
      return;
    }
    setState({ job_id: jobId, status: "queued", logs: [] });

    const ws = new WebSocket(`${WS_BASE}/jobs/${jobId}/ws`);
    ws.onmessage = (event) => {
      setState((s) => (s ? { ...s, logs: [...s.logs, event.data] } : s));
    };

    let cancelled = false;
    (async () => {
      while (!cancelled) {
        try {
          const data = await getJobStatus(jobId);
          setState((s) => (s ? { ...data, logs: s.logs } : data));
          if (data.status === "done" || data.status === "error") break;
        } catch {
          // Le job n'existe pas encore côté Redis juste après l'enqueue : on réessaie.
        }
        await new Promise((r) => setTimeout(r, 1500));
      }
    })();

    return () => {
      cancelled = true;
      ws.close();
    };
  }, [jobId]);

  return state;
}

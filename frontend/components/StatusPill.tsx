const LABELS: Record<string, string> = {
  queued: "En attente",
  running: "En cours",
  done: "Terminé",
  error: "Erreur",
};

const STYLES: Record<string, string> = {
  queued: "bg-surface2 text-dim border-border",
  running: "bg-accent-soft text-accent border-accent/40 animate-pulse",
  done: "bg-success/10 text-success border-success/40",
  error: "bg-danger/10 text-danger border-danger/40",
};

export function StatusPill({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${STYLES[status] ?? STYLES.queued}`}
    >
      {LABELS[status] ?? status}
    </span>
  );
}

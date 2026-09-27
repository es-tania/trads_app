export default function OcrPage() {
  return (
    <div className="space-y-4">
      <h1 className="font-display text-2xl">OCR image</h1>
      <div className="rounded-lg border border-border bg-surface p-6 text-sm text-dim">
        Pas encore branché côté backend — en attente du choix du modèle de vision
        (Ollama local ou API Claude en secours). Voir la Phase 5 dans{" "}
        <code className="font-mono text-xs">docs/ARCHITECTURE.md</code>.
      </div>
    </div>
  );
}

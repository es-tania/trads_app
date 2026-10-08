"use client";

import { useCallback, useEffect, useState } from "react";
import {
  deleteStorageItem,
  listStorageItems,
  storageDownloadUrl,
  StorageCategory,
  StorageItem,
} from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";

const CATEGORY_LABELS: Record<StorageCategory, string> = {
  scripts: "Script scrapé",
  translate: "Traduction .docx",
  subtitles: "Sous-titres",
};

type Filter = "all" | StorageCategory;

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(0)} Ko`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} Mo`;
  return `${(bytes / 1024 ** 3).toFixed(2)} Go`;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
}

export default function HistoryPage() {
  const [items, setItems] = useState<StorageItem[] | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setItems(await listStorageItems());
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Tant qu'un job est actif, on rafraîchit pour voir ses fichiers apparaître.
  const hasActive = items?.some((i) => i.status === "queued" || i.status === "running");
  useEffect(() => {
    if (!hasActive) return;
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, [hasActive, refresh]);

  const visible = items?.filter((i) => filter === "all" || i.category === filter) ?? [];
  const totalSize = visible.reduce((sum, i) => sum + i.size_bytes, 0);

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl">Historique</h1>
          <p className="mt-2 text-dim">
            Tout ce qui est stocké sur le serveur : re-télécharge ou supprime ce dont tu n'as plus besoin.
          </p>
        </div>
        <button
          onClick={refresh}
          className="shrink-0 rounded-md border border-border px-3 py-1.5 text-sm hover:border-accent/50"
        >
          Actualiser
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {(["all", "scripts", "translate", "subtitles"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-md border px-3 py-1.5 text-sm ${
              filter === f ? "border-accent bg-accent-soft" : "border-border text-dim"
            }`}
          >
            {f === "all" ? "Tout" : CATEGORY_LABELS[f]}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}
      {!items && !error && <p className="text-sm text-dim">Chargement…</p>}

      {items && (
        <>
          <p className="text-xs text-dim">
            {visible.length} élément{visible.length > 1 ? "s" : ""} · {formatSize(totalSize)}
          </p>

          {visible.length === 0 ? (
            <div className="rounded-lg border border-border bg-surface p-6 text-sm text-dim">
              Rien à afficher pour l'instant.
            </div>
          ) : (
            <div className="space-y-3">
              {visible.map((item) => (
                <ItemCard key={`${item.category}/${item.id}`} item={item} onDeleted={refresh} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ItemCard({ item, onDeleted }: { item: StorageItem; onDeleted: () => void }) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteStorageItem(item.category, item.id);
      onDeleted();
    } catch (err) {
      setError((err as Error).message);
      setDeleting(false);
      setConfirming(false);
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-medium" title={item.title}>
            {item.title}
          </p>
          <p className="mt-1 text-xs text-dim">
            {CATEGORY_LABELS[item.category]} · {formatDate(item.created_at)} · {formatSize(item.size_bytes)}
          </p>
        </div>
        {item.status && <StatusPill status={item.status} />}
      </div>

      <div className="flex flex-wrap gap-2">
        {item.files.length === 0 ? (
          <span className="text-xs text-dim">Aucun fichier</span>
        ) : (
          item.files.map((file) => (
            <a
              key={file}
              href={storageDownloadUrl(item.category, item.id, file)}
              className="rounded-md border border-border px-2.5 py-1 font-mono text-xs hover:border-accent/50"
            >
              {file}
            </a>
          ))
        )}
      </div>

      <div className="flex items-center justify-end gap-2">
        {error && <span className="mr-auto text-xs text-danger">{error}</span>}
        {confirming ? (
          <>
            <span className="text-xs text-dim">Supprimer définitivement ?</span>
            <button
              onClick={() => setConfirming(false)}
              disabled={deleting}
              className="rounded-md border border-border px-3 py-1 text-xs text-dim"
            >
              Annuler
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="rounded-md bg-danger px-3 py-1 text-xs font-medium text-white disabled:opacity-40"
            >
              {deleting ? "Suppression…" : "Oui, supprimer"}
            </button>
          </>
        ) : (
          <button
            onClick={() => setConfirming(true)}
            className="rounded-md border border-danger/40 px-3 py-1 text-xs text-danger hover:bg-danger/10"
          >
            Supprimer
          </button>
        )}
      </div>
    </div>
  );
}

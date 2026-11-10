"use client";

import { useEffect, useState } from "react";
import { getOcrModels, ocrImages, storageDownloadUrl } from "@/lib/api";
import { JobStatusPanel } from "@/components/JobStatusPanel";

interface ImageEntry {
  file: File;
  url: string;
}

// Tri "naturel" : IMG_2 avant IMG_10, comme l'explorateur Windows.
const naturalCompare = new Intl.Collator("fr", { numeric: true, sensitivity: "base" }).compare;

export default function OcrPage() {
  const [images, setImages] = useState<ImageEntry[]>([]);
  const [models, setModels] = useState<string[] | null>(null);
  const [model, setModel] = useState("");
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  // Empêche un double-clic de lancer deux jobs identiques pendant l'upload.
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOcrModels()
      .then(({ default: def, models }) => {
        setModels(models);
        setModel(models.includes(def) ? def : models[0] ?? "");
      })
      .catch((err) => setModelsError((err as Error).message));
  }, []);

  // Libère les aperçus (object URLs) quand la page est quittée.
  useEffect(() => () => images.forEach((img) => URL.revokeObjectURL(img.url)), []); // eslint-disable-line react-hooks/exhaustive-deps

  function addFiles(list: FileList | null) {
    if (!list) return;
    const added = Array.from(list)
      .filter((f) => f.type.startsWith("image/"))
      .map((file) => ({ file, url: URL.createObjectURL(file) }));
    setImages((prev) => [...prev, ...added].sort((a, b) => naturalCompare(a.file.name, b.file.name)));
  }

  function removeAt(index: number) {
    setImages((prev) => {
      URL.revokeObjectURL(prev[index].url);
      return prev.filter((_, i) => i !== index);
    });
  }

  function move(index: number, delta: number) {
    setImages((prev) => {
      const target = index + delta;
      if (target < 0 || target >= prev.length) return prev;
      const next = [...prev];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function clearAll() {
    images.forEach((img) => URL.revokeObjectURL(img.url));
    setImages([]);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (images.length === 0 || submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      const { job_id } = await ocrImages(images.map((img) => img.file), model || undefined);
      setJobId(job_id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl">OCR image</h1>
        <p className="mt-2 text-dim">
          Importe des captures du jeu, récupère le script transcrit en .docx (modèle de vision local via Ollama).
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            addFiles(e.dataTransfer.files);
          }}
          className={`block cursor-pointer rounded-lg border border-dashed bg-surface p-6 text-center text-sm text-dim hover:border-accent/50 ${
            dragOver ? "border-accent" : "border-border"
          }`}
        >
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            multiple
            className="hidden"
            onChange={(e) => {
              addFiles(e.target.files);
              e.target.value = "";
            }}
          />
          Glisser des images ici ou cliquer pour les choisir (PNG, JPG, WebP)
        </label>

        {images.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm text-dim">
              <span>
                {images.length} image(s) — transcrites dans cet ordre
              </span>
              <button type="button" onClick={clearAll} className="text-xs hover:text-danger">
                Tout retirer
              </button>
            </div>
            <ol className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {images.map((img, i) => (
                <li key={img.url} className="overflow-hidden rounded-md border border-border bg-surface">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={img.url} alt={img.file.name} className="h-40 w-full object-contain bg-surface2" />
                  <div className="flex items-center justify-between gap-1 px-2 py-1 text-xs">
                    <span className="truncate text-dim" title={img.file.name}>
                      {i + 1}. {img.file.name}
                    </span>
                    <span className="flex shrink-0 gap-1">
                      <button type="button" onClick={() => move(i, -1)} disabled={i === 0} className="px-1 disabled:opacity-30" title="Monter">
                        ←
                      </button>
                      <button
                        type="button"
                        onClick={() => move(i, 1)}
                        disabled={i === images.length - 1}
                        className="px-1 disabled:opacity-30"
                        title="Descendre"
                      >
                        →
                      </button>
                      <button type="button" onClick={() => removeAt(i)} className="px-1 hover:text-danger" title="Retirer">
                        ✕
                      </button>
                    </span>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}

        <div className="space-y-1">
          <label htmlFor="ocr-model" className="text-sm font-medium text-dim">
            Modèle de vision (Ollama)
          </label>
          {modelsError ? (
            <p className="text-sm text-danger">{modelsError}</p>
          ) : models === null ? (
            <p className="text-sm text-dim">Chargement des modèles installés…</p>
          ) : (
            <select
              id="ocr-model"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="block rounded-md border border-border bg-surface px-3 py-2 text-sm"
            >
              {models.length === 0 && <option value="">Aucun modèle de vision installé</option>}
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          )}
        </div>

        <button
          type="submit"
          disabled={images.length === 0 || !model || submitting}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {submitting ? "Envoi…" : "Transcrire"}
        </button>
        {error && <p className="text-sm text-danger">{error}</p>}
      </form>

      {jobId && (
        <JobStatusPanel
          jobId={jobId}
          renderDone={() => (
            <a
              href={storageDownloadUrl("ocr", jobId, "script_images.txt")}
              className="rounded-md border border-border px-4 py-2 text-sm hover:border-accent/50"
            >
              Télécharger le .txt
            </a>
          )}
        />
      )}
    </div>
  );
}

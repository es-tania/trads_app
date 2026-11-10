export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const WS_BASE = API_BASE.replace(/^http/, "ws");

export interface JobEnqueued {
  job_id: string;
}

// "deepl" : API officielle (clé requise, palier gratuit 500k caractères/mois).
// "deeplx" : CLI Node.js local (gratuit, sans clé) — moteur par défaut.
export type TranslateEngine = "deepl" | "deeplx";

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
  return res.json();
}

async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
  return res.json();
}

// --- Scraping (module 00) ---

export function scrapeUrl(url: string) {
  return postJson<JobEnqueued>("/scraping/scrape", { url });
}

export function translateScrapedScript(folder: string, filename: string, engine?: TranslateEngine) {
  return postJson<JobEnqueued>("/scraping/translate", { folder, filename, engine });
}

export async function generateScrapedDocx(folder: string, filename: string, lang: "EN" | "FR") {
  const res = await fetch(`${API_BASE}/scraping/generate-docx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder, filename, lang }),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
  return res.json() as Promise<{ folder: string; file: string }>;
}

export function scrapingDownloadUrl(folder: string, filename: string) {
  return `${API_BASE}/scraping/download?folder=${encodeURIComponent(folder)}&filename=${encodeURIComponent(filename)}`;
}

// --- Traduction docx (module 02) ---

export function translateDocx(file: File, engine?: TranslateEngine) {
  const form = new FormData();
  form.append("file", file);
  if (engine) form.append("engine", engine);
  return postForm<JobEnqueued>("/translate/docx", form);
}

// --- OCR d'images (module 01) ---

export interface OcrModels {
  default: string;
  models: string[];
}

export async function getOcrModels(): Promise<OcrModels> {
  const res = await fetch(`${API_BASE}/ocr/models`, { cache: "no-store" });
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
  return res.json();
}

/** Les images sont transcrites dans l'ordre du tableau. */
export function ocrImages(files: File[], model?: string) {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  if (model) form.append("model", model);
  return postForm<JobEnqueued>("/ocr/images", form);
}

// --- Sous-titres (module 03) ---

export interface SubtitlesParams {
  enDocx: File;
  frDocx: File;
  youtubeUrl?: string;
  video?: File;
  whisperModel: string;
  minDuration: number;
}

export function generateSubtitles(params: SubtitlesParams) {
  const form = new FormData();
  form.append("en_docx", params.enDocx);
  form.append("fr_docx", params.frDocx);
  if (params.youtubeUrl) form.append("youtube_url", params.youtubeUrl);
  if (params.video) form.append("video", params.video);
  form.append("whisper_model", params.whisperModel);
  form.append("min_duration", String(params.minDuration));
  return postForm<JobEnqueued>("/subtitles/generate", form);
}

export function subtitlesSrtUrl(jobId: string, lang: "fr" | "en") {
  return `${API_BASE}/subtitles/${jobId}/srt/${lang}`;
}

export function subtitlesVideoUrl(jobId: string) {
  return `${API_BASE}/subtitles/${jobId}/video`;
}

// --- Jobs (générique) ---

export interface JobState {
  job_id: string;
  status: "queued" | "running" | "done" | "error" | "cancelled";
  logs: string[];
  result_filename?: string;
  message?: string;
  [key: string]: unknown;
}

export async function getJobStatus(jobId: string): Promise<JobState> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
  return res.json();
}

export async function cancelJob(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, { method: "POST" });
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
}

export function jobResultUrl(jobId: string) {
  return `${API_BASE}/jobs/${jobId}/result`;
}

// --- Historique (éléments stockés sur disque) ---

export type StorageCategory = "scripts" | "translate" | "subtitles" | "ocr";

export interface StorageItem {
  category: StorageCategory;
  id: string;
  title: string;
  created_at: string;
  files: string[];
  size_bytes: number;
  status: JobState["status"] | null;
  details: Record<string, unknown>;
}

export async function listStorageItems(): Promise<StorageItem[]> {
  const res = await fetch(`${API_BASE}/storage`, { cache: "no-store" });
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
  return res.json();
}

export function storageDownloadUrl(category: StorageCategory, id: string, file: string) {
  return `${API_BASE}/storage/${category}/${encodeURIComponent(id)}/download?file=${encodeURIComponent(file)}`;
}

export async function deleteStorageItem(category: StorageCategory, id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/storage/${category}/${encodeURIComponent(id)}`, { method: "DELETE" });
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
}

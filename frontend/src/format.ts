export function when(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

export function megabytes(bytes: number): string {
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function duration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  const total = Math.max(0, ms) / 1000;
  if (total < 60) return `${total.toFixed(1)}s`;
  const minutes = Math.floor(total / 60);
  const rest = Math.floor(total % 60);
  return `${minutes}m ${rest.toString().padStart(2, "0")}s`;
}

export function jobDuration(job: {
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  status: string;
}, now = Date.now()): string {
  const start = Date.parse(job.started_at || job.created_at);
  const end = job.status === "queued" || job.status === "running" || !job.finished_at
    ? now
    : Date.parse(job.finished_at);
  if (!Number.isFinite(start) || !Number.isFinite(end)) return "—";
  return duration(end - start);
}

export function seconds(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(1)}s`;
}

import type { Health, Job, Limits, MediaItem, MediaKind, MetricHistory, Resources, SwapInput, LoginInput, UserResponse, RegisterInput } from "../types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
  }
}

async function read<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = response.statusText;
    let code: string | undefined;
    try {
      const body = await response.json();
      const detail = body.detail;
      if (detail && typeof detail === "object") {
        message = detail.message ?? message;
        code = detail.code;
      } else if (typeof detail === "string") {
        message = detail;
      }
    } catch {
      /* keep the status text */
    }
    throw new ApiError(message, response.status, code);
  }
  return response.json() as Promise<T>;
}

function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(path, { ...init, credentials: "include" });
}

function query(path: string, q?: string): string {
  const text = q?.trim();
  if (!text) return path;
  return `${path}?q=${encodeURIComponent(text)}`;
}

export function getHealth(): Promise<Health> {
  return apiFetch("/api/health").then((response) => read<Health>(response));
}

export function login(input: LoginInput): Promise<UserResponse> {
  return apiFetch("/api/login", {
    method: "POST", body:
      JSON.stringify(input), headers: { "Content-Type": "application/json" }
  }
  ).then((response) => read<UserResponse>(response))
    .catch((exc) => {
      if (exc instanceof ApiError && exc.status === 401) {
        console.error(exc);
        throw exc;
      } else {
        console.error(exc);
        throw new ApiError("Could not login.", 500, "unknown_error");
      }
    });
}


export function register(input: RegisterInput): Promise<UserResponse> {
  return apiFetch("/api/register", {
    method: "POST", body: JSON.stringify(input),
    headers: { "Content-Type": "application/json" }
  }).then((response) => read<UserResponse>(response))
    .catch((exc) => {
      if (exc instanceof ApiError && exc.status === 401) {
        console.error(exc);
        throw exc;
      } else if (exc instanceof ApiError && exc.status === 409) {
        console.error(exc);
        throw new ApiError("Email already in use.", 409, "email_in_use");
      }
      console.error(exc);
      throw new ApiError("Could not register.", 500, "unknown_error");
    });
}

export function currentUser(): Promise<UserResponse | null> {
  return apiFetch("/api/me").then(async (response) => {
    if (response.status === 401) return null;
    return read<UserResponse>(response);
  });
}

export function logout(): Promise<void> {
  return apiFetch("/api/logout", { method: "POST" }).then((response) => {
    if (!response.ok) return read<void>(response);
  });
}

export function metricHistory(): Promise<MetricHistory> {
  return apiFetch("/api/metrics").then((response) => read<MetricHistory>(response));
}

export function getResources(): Promise<Resources> {
  return apiFetch("/api/resources").then((response) => read<Resources>(response));
}

export function getLimits(): Promise<Limits> {
  return apiFetch("/api/limits").then((response) => read<Limits>(response));
}

export function listJobs(q?: string): Promise<Job[]> {
  return apiFetch(query("/api/jobs", q)).then((response) => read<Job[]>(response));
}

export function getJob(id: number): Promise<Job> {
  return apiFetch(`/api/jobs/${id}`).then((response) => read<Job>(response));
}

export function listMedia(kind: MediaKind, q?: string): Promise<MediaItem[]> {
  return apiFetch(query(`/api/files/${kind}`, q)).then((response) => read<MediaItem[]>(response));
}

export function getMedia(kind: MediaKind, id: number): Promise<MediaItem> {
  return apiFetch(`/api/files/${kind}/${id}`).then((response) => read<MediaItem>(response));
}

export async function downloadBlob(url: string): Promise<Blob> {
  const response = await apiFetch(url);
  if (!response.ok) {
    throw new ApiError("Could not download the file.", response.status);
  }
  return response.blob();
}

export function swap(input: SwapInput): Promise<Job> {
  const body = new FormData();
  input.faces.slice(0, 3).forEach((face, index) => {
    const suffix = index === 0 ? "" : `_${index + 1}`;
    if (face.file) body.append(`source_image${suffix}`, face.file);
    else if (face.id) body.append(`source_image${suffix}_id`, String(face.id));
  });
  body.append("face_order", input.faceOrder);
  if (input.targetVideo) body.append("target_video", input.targetVideo);
  else if (input.targetVideoId) body.append("target_video_id", String(input.targetVideoId));
  return apiFetch("/api/swap", { method: "POST", body }).then((response) => read<Job>(response));
}

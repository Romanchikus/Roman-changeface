export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export type Job = {
  id: number;
  status: JobStatus;
  source_filename: string;
  video_filename: string;
  source_bytes: number;
  video_bytes: number;
  video_duration_sec: number;
  error_code: string | null;
  error_message: string | null;
  model_name: string | null;
  detector_name: string | null;
  inference_ms: number | null;
  simulated: boolean;
  face_order: string;
  note: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  download_url: string | null;
  source_media_id: number | null;
  video_media_id: number | null;
  output_media_id: number | null;
  source_preview_url: string | null;
  video_preview_url: string | null;
  output_preview_url: string | null;
};

export type MediaKind = "images" | "videos" | "outputs";

export type MediaItem = {
  id: number;
  kind: string;
  filename: string;
  size_bytes: number;
  content_type: string;
  duration_sec: number | null;
  created_at: string;
  thumbnail_id: number | null;
  download_url: string;
  preview_url: string | null;
};

export type Limits = {
  max_image_bytes: number;
  max_video_bytes: number;
  max_video_duration_sec: number;
  inference_backend: string;
  gpu_slots: number;
};

export type Health = {
  status: string;
};

export type MetricPoint = {
  sampled_at: string;
  cpu_percent: number | null;
  ram_used_bytes: number;
  ram_total_bytes: number;
  vram_used_bytes: number | null;
  vram_total_bytes: number | null;
  gpu_util_percent: number | null;
};

export type MetricHistory = {
  samples: MetricPoint[];
  inflight: number;
  requests_last_10s: number;
};

export type Resources = {
  cpu_percent: number | null;
  ram_used_bytes: number;
  ram_total_bytes: number;
  vram_used_bytes: number | null;
  vram_total_bytes: number | null;
  gpu_util_percent: number | null;
  job_id: number | null;
  job_status: JobStatus | null;
  elapsed_ms: number | null;
};

export type FaceInput = {
  file?: File | null;
  id?: number | null;
};

export type SwapInput = {
  faces: FaceInput[];
  faceOrder: string;
  targetVideo?: File | null;
  targetVideoId?: number | null;
};


export type LoginInput = {
  email: string;
  password: string;
};

export type UserResponse = {
  id: number;
  email: string;
  created_at: string;
  last_activity_at: string;
};


export interface RegisterInput extends LoginInput {
  password_confirm: string;
};
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError, downloadBlob, getLimits, listMedia } from "../api/client";
import MediaCard from "../components/MediaCard.vue";
import VideoCut from "../components/VideoCut.vue";
import { megabytes } from "../format";
import { useJobs } from "../stores/jobs";
import { trimVideo } from "../trim";
import type { FaceInput, Limits, MediaItem } from "../types";

type FacePick = FaceInput & { key: string; name: string; preview: string | null; owned: boolean };

const router = useRouter();
const jobs = useJobs();
const limits = ref<Limits | null>(null);
const images = ref<MediaItem[]>([]);
const videos = ref<MediaItem[]>([]);
const imageQuery = ref("");
const videoQuery = ref("");
const faces = ref<FacePick[]>([]);
const faceOrder = ref("left-right");
const videoFile = ref<File | null>(null);
const videoId = ref<number | null>(null);
const cutStart = ref(0);
const cutEnd = ref(0);
const cutLength = ref(0);
const videoInput = ref<HTMLInputElement | null>(null);
const error = ref("");
const pending = ref(false);
const cutting = ref(false);

const orders = [
  ["left-right", "Left to right"],
  ["right-left", "Right to left"],
  ["large-small", "Largest first"],
  ["small-large", "Smallest first"],
];

async function loadImages(): Promise<void> {
  images.value = await listMedia("images", imageQuery.value);
}

async function loadVideos(): Promise<void> {
  videos.value = await listMedia("videos", videoQuery.value);
}

onMounted(async () => {
  limits.value = await getLimits();
  await Promise.all([loadImages(), loadVideos()]);
});

onBeforeUnmount(() => {
  for (const face of faces.value) {
    if (face.owned && face.preview) URL.revokeObjectURL(face.preview);
  }
});

function addFace(face: Omit<FacePick, "key">): void {
  if (faces.value.length >= 3) {
    error.value = "You can send up to 3 faces.";
    return;
  }
  error.value = "";
  faces.value.push({ ...face, key: crypto.randomUUID() });
}

function takeImage(event: Event): void {
  const file = (event.target as HTMLInputElement).files?.[0] ?? null;
  if (!file) return;
  addFace({
    file,
    id: null,
    name: file.name,
    preview: URL.createObjectURL(file),
    owned: true,
  });
  (event.target as HTMLInputElement).value = "";
}

function chooseImage(item: MediaItem): void {
  const index = faces.value.findIndex((face) => face.id === item.id);
  if (index >= 0) {
    removeFace(index);
    return;
  }
  addFace({ file: null, id: item.id, name: item.filename, preview: item.preview_url, owned: false });
}

function removeFace(index: number): void {
  const [face] = faces.value.splice(index, 1);
  if (face?.owned && face.preview) URL.revokeObjectURL(face.preview);
}

function moveFace(index: number, step: number): void {
  const next = index + step;
  if (next < 0 || next >= faces.value.length) return;
  const [face] = faces.value.splice(index, 1);
  if (face) faces.value.splice(next, 0, face);
}

function orderOf(item: MediaItem): number | null {
  const index = faces.value.findIndex((face) => face.id === item.id);
  return index < 0 ? null : index + 1;
}

function takeVideo(event: Event): void {
  const file = (event.target as HTMLInputElement).files?.[0] ?? null;
  videoFile.value = file;
  if (file) videoId.value = null;
}

function chooseVideo(item: MediaItem): void {
  videoId.value = item.id;
  videoFile.value = null;
  if (videoInput.value) videoInput.value.value = "";
}

async function videoToSend(): Promise<{ file: File | null; id: number | null }> {
  if (!videoFile.value && !videoId.value) return { file: null, id: null };
  if (cutLength.value <= 0) throw new Error("Wait for the video to finish loading.");
  const span = cutEnd.value - cutStart.value;
  const max = limits.value?.max_video_duration_sec ?? 30;
  if (span > max + 0.05) {
    throw new Error(`This cut is ${span.toFixed(1)}s. The limit is ${max}s.`);
  }
  const trimmed = cutStart.value >= 0.05 || cutEnd.value < cutLength.value - 0.05;
  if (videoFile.value) {
    if (!trimmed) return { file: videoFile.value, id: null };
    cutting.value = true;
    return { file: await trimVideo(videoFile.value, cutStart.value, cutEnd.value), id: null };
  }
  if (!trimmed) return { file: null, id: videoId.value };
  const item = videos.value.find((video) => video.id === videoId.value);
  if (!item) throw new Error("Target video was not found.");
  cutting.value = true;
  const blob = await downloadBlob(item.download_url);
  const file = new File([blob], item.filename || "clip.mp4", { type: blob.type || "video/mp4" });
  return { file: await trimVideo(file, cutStart.value, cutEnd.value), id: null };
}

async function submit(): Promise<void> {
  if (faces.value.length === 0 || (!videoFile.value && !videoId.value)) {
    error.value = "Choose at least one source face and a target video.";
    return;
  }
  pending.value = true;
  error.value = "";
  try {
    const video = await videoToSend();
    cutting.value = false;
    const id = await jobs.submit({
      faces: faces.value.map((face) => ({ file: face.file, id: face.id })),
      faceOrder: faceOrder.value,
      targetVideo: video.file,
      targetVideoId: video.id,
    });
    await router.push(`/jobs/${id}`);
  } catch (exc) {
    error.value = exc instanceof ApiError ? exc.message : exc instanceof Error ? exc.message : "Could not queue the swap.";
  } finally {
    cutting.value = false;
    pending.value = false;
  }
}
</script>

<template>
  <section class="stage">
    <header class="stage-head">
      <div>
        <p class="eyebrow">Queue</p>
        <h1>Pick faces and a clip.</h1>
        <p class="lede" v-if="limits">
          Up to 3 faces, images up to {{ megabytes(limits.max_image_bytes) }}, videos up to
          {{ megabytes(limits.max_video_bytes) }} and {{ limits.max_video_duration_sec }} seconds.
          One {{ limits.inference_backend }} job at a time.
        </p>
      </div>
      <button type="button" :disabled="pending" @click="submit">
        {{ cutting ? "Cutting…" : pending ? "Sending…" : "Queue swap" }}
      </button>
    </header>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="columns">
      <section>
        <div class="row">
          <h2>Source faces</h2>
          <input v-model="imageQuery" type="search" placeholder="Search images" @change="loadImages" />
        </div>
        <label class="drop">
          Add a new face
          <input type="file" accept="image/png,image/jpeg,image/webp" @change="takeImage" />
        </label>
        <ol v-if="faces.length" class="faces">
          <li v-for="(face, index) in faces" :key="face.key">
            <img v-if="face.preview" :src="face.preview" alt="" />
            <span>{{ index + 1 }}. {{ face.name }}</span>
            <button type="button" class="ghost" :disabled="index === 0" @click="moveFace(index, -1)">Earlier</button>
            <button type="button" class="ghost" :disabled="index === faces.length - 1" @click="moveFace(index, 1)">Later</button>
            <button type="button" class="ghost" @click="removeFace(index)">Remove</button>
          </li>
        </ol>
        <label class="order">
          When the clip has several people
          <select v-model="faceOrder">
            <option v-for="[value, label] in orders" :key="value" :value="value">{{ label }}</option>
          </select>
        </label>
        <div class="grid">
          <MediaCard
            v-for="item in images"
            :key="item.id"
            :item="item"
            :selected="orderOf(item) !== null"
            :badge="orderOf(item)"
            @choose="chooseImage(item)"
          />
        </div>
        <p v-if="images.length === 0" class="muted">No images yet.</p>
      </section>
      <section>
        <div class="row">
          <h2>Target video</h2>
          <input v-model="videoQuery" type="search" placeholder="Search videos" @change="loadVideos" />
        </div>
        <label class="drop">
          {{ videoFile ? videoFile.name : "Upload a new video" }}
          <input
            ref="videoInput"
            type="file"
            accept="video/mp4,video/webm,video/quicktime"
            @change="takeVideo"
          />
        </label>
        <div class="grid">
          <article v-if="videoFile" class="card selected">
            <VideoCut v-model:start="cutStart" v-model:end="cutEnd" v-model:length="cutLength" :file="videoFile" />
            <div class="card-body">
              <strong>{{ videoFile.name }}</strong>
              <p>Drag either edge of the gold bar.</p>
            </div>
          </article>
          <MediaCard
            v-for="item in videos"
            :key="item.id"
            :item="item"
            :selected="videoId === item.id"
            @choose="chooseVideo(item)"
          >
            <template v-if="videoId === item.id" #player>
              <VideoCut
                v-model:start="cutStart"
                v-model:end="cutEnd"
                v-model:length="cutLength"
                :src="item.download_url"
              />
            </template>
          </MediaCard>
        </div>
        <p v-if="videos.length === 0 && !videoFile" class="muted">No videos yet.</p>
      </section>
    </div>
  </section>
</template>

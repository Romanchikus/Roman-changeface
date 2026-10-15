<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { ApiError, getMedia, listMedia } from "../api/client";
import MediaCard from "../components/MediaCard.vue";
import { megabytes, seconds, when } from "../format";
import type { MediaItem, MediaKind } from "../types";

const kind = ref<MediaKind>("images");
const query = ref("");
const items = ref<MediaItem[]>([]);
const detail = ref<MediaItem | null>(null);
const error = ref("");

const tabs: { id: MediaKind; label: string }[] = [
  { id: "images", label: "Images" },
  { id: "videos", label: "Videos" },
  { id: "outputs", label: "Outputs" },
];

async function load(): Promise<void> {
  error.value = "";
  detail.value = null;
  try {
    items.value = await listMedia(kind.value, query.value);
  } catch (exc) {
    error.value = exc instanceof ApiError ? exc.message : "Could not load files.";
  }
}

async function open(item: MediaItem): Promise<void> {
  detail.value = await getMedia(kind.value, item.id);
}

onMounted(load);
watch(kind, load);
</script>

<template>
  <section class="stage">
    <header class="stage-head">
      <div>
        <p class="eyebrow">Library</p>
        <h1>Files already on the server.</h1>
      </div>
      <input v-model="query" type="search" placeholder="Search filename" @change="load" />
    </header>
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        :class="{ active: kind === tab.id }"
        @click="kind = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="library">
      <div class="grid">
        <MediaCard v-for="item in items" :key="item.id" :item="item" :selected="detail?.id === item.id" @choose="open(item)" />
      </div>
      <aside v-if="detail" class="detail">
        <video
          v-if="detail.kind === 'video'"
          class="player"
          controls
          playsinline
          :src="detail.download_url"
        />
        <img v-else-if="detail.preview_url" :src="detail.preview_url" :alt="detail.filename" />
        <h2>{{ detail.filename }}</h2>
        <dl>
          <div><dt>Id</dt><dd>{{ detail.id }}</dd></div>
          <div><dt>Kind</dt><dd>{{ detail.kind }}</dd></div>
          <div><dt>Type</dt><dd>{{ detail.content_type }}</dd></div>
          <div><dt>Size</dt><dd>{{ megabytes(detail.size_bytes) }}</dd></div>
          <div><dt>Duration</dt><dd>{{ seconds(detail.duration_sec) }}</dd></div>
          <div><dt>Added</dt><dd>{{ when(detail.created_at) }}</dd></div>
        </dl>
        <a v-if="detail.kind !== 'video'" class="button" :href="detail.download_url">Download</a>
      </aside>
    </div>
    <p v-if="items.length === 0" class="muted">Nothing in this folder.</p>
  </section>
</template>

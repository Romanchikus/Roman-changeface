<script setup lang="ts">
import { megabytes, seconds, when } from "../format";
import type { MediaItem } from "../types";

defineProps<{
  item: MediaItem;
  selected?: boolean;
  badge?: number | null;
}>();

defineEmits<{
  choose: [];
}>();
</script>

<template>
  <article class="card" :class="{ selected }">
    <span v-if="badge" class="badge">{{ badge }}</span>
    <slot v-if="$slots.player" name="player" />
    <button v-else type="button" class="preview" @click="$emit('choose')">
      <img v-if="item.preview_url" :src="item.preview_url" :alt="item.filename" />
      <span v-else class="empty-preview">No preview</span>
    </button>
    <div class="card-body">
      <strong>{{ item.filename }}</strong>
      <p>{{ megabytes(item.size_bytes) }} · {{ seconds(item.duration_sec) }} · {{ when(item.created_at) }}</p>
      <a v-if="item.kind !== 'video'" :href="item.download_url">Download</a>
    </div>
  </article>
</template>

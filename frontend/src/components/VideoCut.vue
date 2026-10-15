<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { seconds } from "../format";

const props = defineProps<{ file?: File | null; src?: string | null }>();
const start = defineModel<number>("start", { required: true });
const end = defineModel<number>("end", { required: true });
const length = defineModel<number>("length", { required: true });

const player = ref<HTMLVideoElement | null>(null);
const film = ref<HTMLElement | null>(null);
const duration = ref(0);
const url = ref("");
const owned = ref(false);

const keepStyle = computed(() => {
  const span = duration.value || 1;
  return {
    left: `${(start.value / span) * 100}%`,
    width: `${((end.value - start.value) / span) * 100}%`,
  };
});

watch(
  () => [props.file, props.src] as const,
  ([file, src]) => {
    if (owned.value && url.value) URL.revokeObjectURL(url.value);
    owned.value = Boolean(file);
    url.value = file ? URL.createObjectURL(file) : src || "";
    duration.value = 0;
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  if (owned.value && url.value) URL.revokeObjectURL(url.value);
});

function loaded(): void {
  const measured = player.value?.duration ?? 0;
  duration.value = Number.isFinite(measured) ? measured : 0;
  length.value = duration.value;
  start.value = 0;
  end.value = duration.value;
  if (player.value) player.value.currentTime = 0;
}

function timeAt(event: PointerEvent): number {
  const rect = film.value?.getBoundingClientRect();
  if (!rect || rect.width === 0) return 0;
  const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
  return ratio * duration.value;
}

function drag(side: "start" | "end", event: PointerEvent): void {
  const move = (ev: PointerEvent) => {
    const time = timeAt(ev);
    if (side === "start") {
      start.value = Math.min(Math.max(0, time), Math.max(0, end.value - 0.1));
      if (player.value) player.value.currentTime = start.value;
    } else {
      end.value = Math.max(Math.min(duration.value, time), start.value + 0.1);
    }
  };
  const stop = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", stop);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", stop);
  move(event);
}

function tick(): void {
  const video = player.value;
  if (!video || end.value <= start.value) return;
  if (video.currentTime < start.value || video.currentTime >= end.value) {
    video.currentTime = start.value;
  }
}

function toggle(): void {
  const video = player.value;
  if (!video) return;
  if (video.paused) void video.play();
  else video.pause();
}
</script>

<template>
  <div class="stage-video">
    <video
      ref="player"
      class="player"
      :src="url"
      playsinline
      @loadedmetadata="loaded"
      @timeupdate="tick"
      @click="toggle"
    />
    <div ref="film" class="film">
      <div class="film-keep" :style="keepStyle">{{ seconds(start) }}–{{ seconds(end) }}</div>
      <button type="button" class="handle" :style="{ left: keepStyle.left }" aria-label="Cut start" @pointerdown="drag('start', $event)" />
      <button
        type="button"
        class="handle"
        :style="{ left: `calc(${keepStyle.left} + ${keepStyle.width})` }"
        aria-label="Cut end"
        @pointerdown="drag('end', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { metricHistory } from "../api/client";
import type { MetricHistory, MetricPoint } from "../types";

const history = ref<MetricHistory | null>(null);
const points = ref<MetricPoint[]>([]);
let events: EventSource | null = null;

const bars = computed(() => points.value.slice(-60));
const ticks = [100, 75, 50, 25, 0];

function remember(point: MetricPoint): void {
  if (points.value.some((item) => item.sampled_at === point.sampled_at)) return;
  points.value = [...points.value, point];
}

function pct(value: number | null): string {
  const clamped = Math.max(0, Math.min(100, value ?? 0));
  return `${clamped}%`;
}

function clock(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { minute: "2-digit", second: "2-digit", hour12: false });
}

function vram(point: MetricPoint): number | null {
  if (!point.vram_total_bytes) return null;
  return ((point.vram_used_bytes ?? 0) / point.vram_total_bytes) * 100;
}

onMounted(async () => {
  history.value = await metricHistory();
  points.value = history.value.samples;
  events = new EventSource("/api/metrics/events");
  events.addEventListener("sample", (event) => {
    remember(JSON.parse((event as MessageEvent).data) as MetricPoint);
  });
});

onUnmounted(() => {
  events?.close();
});
</script>

<template>
  <section class="stage">
    <header class="stage-head">
      <div>
        <p class="eyebrow">Metrics</p>
        <h1>Resource samples</h1>
      </div>
    </header>
    <div class="legend">
      <span><i class="cpu"></i>CPU</span>
      <span><i class="gpu"></i>GPU</span>
      <span><i class="vram"></i>VRAM</span>
    </div>
    <p class="muted">{{ bars.length }} of {{ points.length }} samples, oldest at the left.</p>
    <div class="chart">
      <div class="scale">
        <span v-for="tick in ticks" :key="`l-${tick}`">{{ tick }}</span>
      </div>
      <div class="plot">
        <div v-for="point in bars" :key="point.sampled_at" class="slot">
          <div class="bar cpu" :style="{ height: pct(point.cpu_percent) }"></div>
          <div class="bar gpu" :style="{ height: pct(point.gpu_util_percent) }"></div>
          <div class="bar vram" :style="{ height: pct(vram(point)) }"></div>
        </div>
      </div>
      <div class="scale right">
        <span v-for="tick in ticks" :key="`r-${tick}`">{{ tick }}</span>
      </div>
      <div class="times">
        <span v-for="point in bars" :key="`t-${point.sampled_at}`">{{ clock(point.sampled_at) }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.legend {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  justify-content: center;
}

.legend span {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend i {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.chart {
  display: grid;
  grid-template-columns: 36px 1fr 36px;
  grid-template-rows: 220px 64px;
  column-gap: 8px;
  padding: 12px;
  background: #1d1a17;
  border: 1px solid #322c26;
  border-radius: 16px;
}

.scale {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 220px;
  color: #b7aea2;
  font-size: 0.7rem;
}

.scale.right {
  text-align: right;
}

.plot {
  display: flex;
  align-items: flex-end;
  gap: 1px;
  height: 220px;
}

.times {
  grid-column: 2;
  display: flex;
  height: 64px;
  width: 100%;
  font-weight: bold;
}

.times span {
  flex: 1;
  min-width: 0;
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  font-size: 0.62rem;
  line-height: 1;
  color: #359163;
  white-space: nowrap;
}

.slot {
  flex: 1;
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 100%;
  min-width: 0;
}

.bar {
  flex: 1;
  min-height: 2px;
  border-radius: 3px 3px 0 0;
}

.cpu {
  background: #f0c27a;
}

.gpu {
  background: #8fb9a8;
}

.vram {
  background: #d28b7a;
}
</style>

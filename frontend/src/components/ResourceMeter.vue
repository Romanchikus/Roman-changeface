<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { getResources } from "../api/client";
import { duration, megabytes } from "../format";
import type { Resources } from "../types";

const sample = ref<Resources | null>(null);
let timer = 0;

async function tick(): Promise<void> {
  try {
    sample.value = await getResources();
  } catch {
    sample.value = null;
  }
}

onMounted(() => {
  void tick();
  timer = window.setInterval(() => void tick(), 2000);
});

onUnmounted(() => window.clearInterval(timer));
</script>

<template>
  <aside class="meters" v-if="sample">
    <span>CPU {{ sample.cpu_percent == null ? "…" : `${sample.cpu_percent}%` }}</span>
    <span>RAM {{ megabytes(sample.ram_used_bytes) }} / {{ megabytes(sample.ram_total_bytes) }}</span>
    <span v-if="sample.vram_total_bytes != null">
      VRAM {{ megabytes(sample.vram_used_bytes || 0) }} / {{ megabytes(sample.vram_total_bytes) }}
      <template v-if="sample.gpu_util_percent != null"> · {{ sample.gpu_util_percent }}%</template>
    </span>
    <RouterLink v-if="sample.job_id" class="meter-job" :to="`/jobs/${sample.job_id}`">
      Job {{ sample.job_id }}
      <em :class="sample.job_status || ''">{{ sample.job_status }}</em>
      {{ duration(sample.elapsed_ms) }}
    </RouterLink>
    <span v-else>No jobs yet</span>
  </aside>
</template>

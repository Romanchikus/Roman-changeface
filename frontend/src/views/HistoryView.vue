<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { listJobs } from "../api/client";
import { jobDuration, when } from "../format";
import type { Job } from "../types";

const jobs = ref<Job[]>([]);
const query = ref("");
const now = ref(Date.now());
const clock = window.setInterval(() => {
  now.value = Date.now();
}, 500);
onUnmounted(() => window.clearInterval(clock));

async function load(): Promise<void> {
  jobs.value = await listJobs(query.value);
}

onMounted(load);
</script>

<template>
  <section class="stage">
    <header class="stage-head">
      <div>
        <p class="eyebrow">History</p>
        <h1>Jobs</h1>
      </div>
      <input v-model="query" type="search" placeholder="Search id, status, model, filename" @change="load" />
    </header>
    <p v-if="jobs.length === 0" class="muted">No swaps yet.</p>
    <div v-else class="job-list">
      <RouterLink v-for="job in jobs" :key="job.id" class="job-row" :to="`/jobs/${job.id}`">
        <img v-if="job.source_preview_url" :src="job.source_preview_url" alt="" />
        <span v-else class="empty-preview small"></span>
        <div>
          <strong>#{{ job.id }} {{ job.source_filename }}</strong>
          <p>{{ job.video_filename }}</p>
        </div>
        <em :class="job.status">{{ job.status }}</em>
        <span>{{ jobDuration(job, now) }} · {{ when(job.created_at) }}</span>
      </RouterLink>
    </div>
  </section>
</template>

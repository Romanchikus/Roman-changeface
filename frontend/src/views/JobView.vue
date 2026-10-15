<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { useJobPoll } from "../composables/useJobPoll";
import { jobDuration, seconds, when } from "../format";

const props = defineProps<{ id: string }>();
const jobId = computed(() => Number(props.id));
const { job, error } = useJobPoll(jobId);
const now = ref(Date.now());
const clock = window.setInterval(() => {
  now.value = Date.now();
}, 500);
onUnmounted(() => window.clearInterval(clock));
</script>

<template>
  <section class="stage" v-if="job">
    <p class="eyebrow">Job {{ job.id }}</p>
    <header class="stage-head">
      <h1 :class="job.status">{{ job.status }}</h1>
      <RouterLink class="button ghost" to="/history">All jobs</RouterLink>
    </header>
    <p class="lede">{{ job.source_filename }} onto {{ job.video_filename }} · {{ seconds(job.video_duration_sec) }}</p>
    <p v-if="job.note" class="note">{{ job.note }}</p>
    <p v-if="job.error_message" class="error">{{ job.error_message }}</p>
    <div class="frames">
      <figure>
        <img v-if="job.source_preview_url" :src="job.source_preview_url" alt="Source" />
        <figcaption>Source</figcaption>
      </figure>
      <figure>
        <video
          v-if="job.video_media_id"
          class="player"
          controls
          playsinline
          :src="`/api/files/videos/${job.video_media_id}/download`"
        />
        <figcaption>Target video</figcaption>
      </figure>
      <figure>
        <video v-if="job.download_url" class="player" controls playsinline :src="job.download_url" />
        <img v-else-if="job.output_preview_url" :src="job.output_preview_url" alt="Output" />
        <figcaption>Output</figcaption>
      </figure>
    </div>
    <dl>
      <div><dt>Created</dt><dd>{{ when(job.created_at) }}</dd></div>
      <div><dt>Started</dt><dd>{{ when(job.started_at) }}</dd></div>
      <div><dt>Finished</dt><dd>{{ when(job.finished_at) }}</dd></div>
      <div><dt>Model</dt><dd>{{ job.model_name || "—" }}</dd></div>
      <div><dt>Detector</dt><dd>{{ job.detector_name || "—" }}</dd></div>
      <div><dt>{{ job.status === "queued" || job.status === "running" ? "Taking" : "Took" }}</dt><dd>{{ jobDuration(job, now) }}</dd></div>
      <div><dt>Inference</dt><dd>{{ job.inference_ms != null ? `${job.inference_ms} ms` : "—" }}</dd></div>
    </dl>
  </section>
  <section class="stage" v-else>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-else class="muted">Loading job {{ id }}…</p>
  </section>
</template>

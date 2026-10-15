import { onUnmounted, ref, type Ref } from "vue";
import { getJob } from "../api/client";
import type { Job } from "../types";

export function useJobPoll(id: Ref<number>) {
  const job = ref<Job | null>(null);
  const error = ref("");
  let timer = 0;

  async function tick(): Promise<void> {
    try {
      job.value = await getJob(id.value);
      error.value = "";
      if (job.value.status === "queued" || job.value.status === "running") {
        timer = window.setTimeout(() => void tick(), 1500);
      }
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : "Could not load the job.";
    }
  }

  void tick();
  onUnmounted(() => window.clearTimeout(timer));
  return { job, error };
}

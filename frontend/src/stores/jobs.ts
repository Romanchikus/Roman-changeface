import { defineStore } from "pinia";
import { ref } from "vue";
import { getJob, listJobs, swap } from "../api/client";
import type { Job, SwapInput } from "../types";

export const useJobs = defineStore("jobs", () => {
  const jobs = ref<Job[]>([]);
  const current = ref<Job | null>(null);

  async function refresh(): Promise<void> {
    jobs.value = await listJobs();
  }

  async function load(id: number): Promise<Job> {
    current.value = await getJob(id);
    return current.value;
  }

  async function submit(input: SwapInput): Promise<number> {
    const created = await swap(input);
    current.value = created;
    return created.id;
  }

  return { jobs, current, refresh, load, submit };
});

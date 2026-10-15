<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink, RouterView } from "vue-router";
import { getHealth, getLimits } from "./api/client";
import ResourceMeter from "./components/ResourceMeter.vue";
import { useSession } from "./stores/session";

const health = ref("…");
const backend = ref("");
const session = useSession();

onMounted(async () => {
  try {
    const [live, limits] = await Promise.all([getHealth(), getLimits(), session.refresh()]);
    health.value = live.status;
    backend.value = limits.inference_backend;
  } catch {
    health.value = "down";
  }
});
</script>

<template>
  <div class="shell">
    <header class="top">
      <RouterLink class="mark" to="/">Changeface</RouterLink>
      <nav>
        <RouterLink to="/">Swap</RouterLink>
        <RouterLink to="/library">Library</RouterLink>
        <RouterLink to="/history">Jobs</RouterLink>
        <RouterLink to="/metrics">Metrics</RouterLink>
        <RouterLink v-if="!session.user" to="/login">Login</RouterLink>
        <button v-else type="button" class="ghost" @click="session.signOut()">{{ session.user.email }}</button>
      </nav>
      <p class="status" :class="health">{{ health }}<span v-if="backend"> · {{ backend }}</span></p>
    </header>
      <ResourceMeter v-if="session.user" />
    <main>
      <RouterView />
    </main>
  </div>
</template>

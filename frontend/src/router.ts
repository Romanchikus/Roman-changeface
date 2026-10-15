import { createRouter, createWebHistory } from "vue-router";
import HistoryView from "./views/HistoryView.vue";
import JobView from "./views/JobView.vue";
import LibraryView from "./views/LibraryView.vue";
import SwapView from "./views/SwapView.vue";
import LoginView from "./views/LoginView.vue";
import MetricsView from "./views/MetricsView.vue";
import { useSession } from "./stores/session";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "swap", component: SwapView },
    { path: "/library", name: "library", component: LibraryView },
    { path: "/jobs/:id", name: "job", component: JobView, props: true },
    { path: "/history", name: "history", component: HistoryView },
    { path: "/login", name: "login", component: LoginView },
    { path: "/metrics", name: "metrics", component: MetricsView },
  ],
});

router.beforeEach(async (to) => {
  if (to.name === "login") return true;
  const session = useSession();
  if (!session.user) await session.refresh();
  if (!session.user) return { name: "login" };
  return true;
});

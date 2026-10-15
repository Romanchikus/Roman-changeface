import { defineStore } from "pinia";
import { ref } from "vue";
import { currentUser, logout } from "../api/client";
import type { UserResponse } from "../types";

export const useSession = defineStore("session", () => {
  const user = ref<UserResponse | null>(null);

  async function refresh(): Promise<void> {
    user.value = await currentUser();
  }

  async function signOut(): Promise<void> {
    await logout();
    user.value = null;
  }

  return { user, refresh, signOut };
});

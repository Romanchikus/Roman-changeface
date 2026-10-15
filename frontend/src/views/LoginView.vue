<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { login as loginApi, register as registerApi } from "../api/client";
import { ApiError } from "../api/client";
import type { LoginInput, RegisterInput } from "../types";
import type { UserResponse } from "../types";
import { useSession } from "../stores/session";
const email = ref<string>("");
const password = ref<string>("");
const password_confirm = ref<string>("");
const error = ref<string>("");
const pending = ref(false);
const is_register = ref(false);
const user = ref<UserResponse | null>(null);
const session = useSession();
const router = useRouter();

function toggle_register(to_register: boolean): void {
    is_register.value = to_register;
    email.value = email.value.trim().toLowerCase();
    password.value = password.value.trim();
    password_confirm.value = password_confirm.value.trim();
}

async function submit(): Promise<void> {
    if (!validate()) {
        return;
    }
    if (is_register.value) {
        await register();
    } else {
        await login();
    }
}
async function login(): Promise<void> {
    error.value = "";
    pending.value = true;
    const input: LoginInput = { email: email.value.trim(), password: password.value.trim() };
    try {
        user.value = await loginApi(input);
        session.user = user.value;
        await router.push("/");
    } catch (exc) {
        error.value = exc instanceof ApiError ? exc.message : "Could not login.";
    } finally {
        pending.value = false;
        toggle_register(false);
    }
}

async function register(): Promise<void> {
    error.value = "";
    pending.value = true;
    const input: RegisterInput = { email: email.value.trim().toLowerCase(), password: password.value.trim(), password_confirm: password.value.trim() };
    try {
        await registerApi(input);
        await login();
    } catch (exc) {
        error.value = exc instanceof ApiError ? exc.message : "Could not register.";
    } finally {
        pending.value = false;
    }
    toggle_register(false);
}

function validate(): boolean {
    if (email.value.trim().length === 0) {
        error.value = "Email is required.";
        return false;
    }
    if (password.value.trim().length === 0) {
        error.value = "Password is required.";
        return false;
    }
    if (is_register.value) {
        if (password.value.trim() !== password_confirm.value.trim()) {
            error.value = "Passwords do not match.";
            return false;
        }
    }
    return true;
}

</script>

<template>
    <section class="stage" v-if="!user">
        <header class="stage-head">
            <h1>Login or Register</h1>
        </header>
        <div class="center-form">
            <form @submit.prevent="submit" class="form-container login-container">
                <div class="mode-switch" role="group" aria-label="Login or register">
                    <button type="button" :class="{ active: !is_register }" :disabled="pending"
                        @click="toggle_register(false)">To login</button>
                    <button type="button" :class="{ active: is_register }" :disabled="pending"
                        @click="toggle_register(true)">To register</button>
                </div>
                <div class="form-group">
                    <div class="class input-container">
                        <label for="email" class="form-header">Email</label>
                        <input v-model="email" type="email" id="email" required :class="{ filled: email.length > 0 }" />
                        <label for="password" class="form-header">Password</label>
                        <input v-model="password" type="password" id="password" required :class="{ filled: password.length > 0 }" />
                        <div v-if="is_register">
                            <label for="password_confirm" class="form-header">Confirm Password</label>
                            <input v-model="password_confirm" type="password" id="password_confirm" required :class="{ filled: password_confirm.length > 0 }" />
                        </div>
                    </div>
                    <p class="lede">Enter your email and password to login or register.</p>
                </div>
                <button type="submit" class="button" :disabled="pending">{{ is_register ? "Register" : "Login"
                    }}</button>
            </form>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
    </section>
    <section class="stage" v-else>
        <header class="stage-head">
            <div class="user-info">
                <p>Email: {{ user?.email }}</p>
                <p>Created at: {{ user?.created_at }}</p>
                <p>Last activity at: {{ user?.last_activity_at }}</p>
            </div>
        </header>
    </section>
</template>
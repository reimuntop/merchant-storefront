<script setup>
import { computed, ref } from "vue";
import { LogIn, UserPlus } from "lucide-vue-next";
import { request, storeUser } from "../api";

const logoUrl = "/toktok-mark.svg";

const emit = defineEmits(["authenticated"]);

const mode = ref("login");
const username = ref("");
const displayName = ref("");
const password = ref("");
const error = ref("");
const busy = ref(false);

const isRegister = computed(() => mode.value === "register");
const passwordStrength = computed(() => {
  if (!password.value) return 0;
  let score = 0;
  if (password.value.length >= 8) score += 1;
  if (/[a-z]/.test(password.value) && /[A-Z]/.test(password.value)) score += 1;
  if (/\d/.test(password.value)) score += 1;
  if (/[^A-Za-z0-9]/.test(password.value)) score += 1;
  return score;
});
const passwordStrengthLabel = computed(() => ["", "Weak", "Fair", "Good", "Strong"][passwordStrength.value]);
const passwordStrengthColor = computed(() => ["#e6e9e5", "#c95b45", "#e4a72c", "#74a83b", "#176b2a"][passwordStrength.value]);

async function submit() {
  error.value = "";
  if (isRegister.value && passwordStrength.value < 3) {
    error.value = "Password is too weak. Use at least 8 characters with uppercase, lowercase, and numbers.";
    return;
  }
  busy.value = true;
  try {
    const result = await request(isRegister.value ? "/api/register" : "/api/login", {
      method: "POST",
      body: JSON.stringify({
        username: username.value,
        display_name: displayName.value || username.value,
        password: password.value,
      }),
    });
    const authenticatedUser = { ...result.user, access_token: result.access_token };
    storeUser(authenticatedUser);
    emit("authenticated", authenticatedUser);
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="auth-shell grid min-h-screen place-items-center px-5 py-10">
    <section class="r-modal w-full max-w-md border border-line bg-white p-6 shadow-[0_1px_2px_rgba(32,31,26,.06),0_16px_40px_rgba(32,31,26,.08)] sm:p-8">
      <div class="flex items-center gap-3">
        <img :src="logoUrl" alt="Belanjoo" class="h-11 w-11" />
        <div>
          <p class="text-lg font-bold leading-5 text-ink">Belanjoo</p>
          <p class="text-xs text-[#5c5a50]">Everyday goods, from local sellers.</p>
        </div>
      </div>

      <form @submit.prevent="submit">
        <div class="mt-6 mb-5 flex border border-line bg-field p-1 r-ctl">
          <button
            type="button"
            class="flex flex-1 items-center justify-center gap-2 px-3 py-2 text-sm font-semibold r-ctl"
            :class="mode === 'login' ? 'bg-white shadow-sm' : 'text-[#68635d]'"
            @click="mode = 'login'"
          >
            <LogIn class="h-4 w-4" />
            Login
          </button>
          <button
            type="button"
            class="flex flex-1 items-center justify-center gap-2 px-3 py-2 text-sm font-semibold r-ctl"
            :class="mode === 'register' ? 'bg-white shadow-sm' : 'text-[#68635d]'"
            @click="mode = 'register'"
          >
            <UserPlus class="h-4 w-4" />
            Register
          </button>
        </div>

        <h1 class="text-2xl font-bold tracking-tight">{{ isRegister ? "Create your account" : "Welcome back" }}</h1>
        <p class="mt-2 text-sm text-[#5c5a50]">{{ isRegister ? "Shop, order, and keep your purchase history in one place." : "Access your cart, orders, and product questions." }}</p>

        <label class="mt-6 block text-sm font-medium text-[#4d4944]" for="username">Username</label>
        <input
          id="username"
          v-model="username"
          class="mt-2 w-full border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss r-ctl"
          autocomplete="username"
        />

        <label v-if="isRegister" class="mt-4 block text-sm font-medium text-[#4d4944]" for="displayName">Display name</label>
        <input
          v-if="isRegister"
          id="displayName"
          v-model="displayName"
          class="mt-2 w-full border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss r-ctl"
          autocomplete="name"
        />

        <label class="mt-4 block text-sm font-medium text-[#4d4944]" for="password">Password</label>
        <input
          id="password"
          v-model="password"
          type="password"
          class="mt-2 w-full border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss r-ctl"
          :autocomplete="isRegister ? 'new-password' : 'current-password'"
        />

        <div v-if="isRegister" class="mt-3">
          <div class="flex gap-1.5" aria-label="Password strength">
            <span v-for="bar in 4" :key="bar" class="h-1.5 flex-1 rounded-full" :style="{ backgroundColor: bar <= passwordStrength ? passwordStrengthColor : '#e4ece5' }"></span>
          </div>
          <div class="mt-2 text-xs">
            <span :class="passwordStrength ? 'font-semibold text-ink' : 'text-[#5c5a50]'">{{ passwordStrengthLabel || "Check password strength" }}</span>
          </div>
        </div>

        <p v-if="error" class="mt-4 border border-ember bg-[#f8eae5] px-3 py-2 text-sm text-ember r-ctl">
          {{ error }}
        </p>

        <button class="primary-button mt-6 w-full r-ctl" :disabled="busy">
          <component :is="isRegister ? UserPlus : LogIn" class="h-4 w-4" />
          {{ isRegister ? "Register" : "Login" }}
        </button>
      </form>

      <p class="mt-6 border-t border-line pt-4 text-center text-xs text-[#5c5a50]">Registered customers review products after purchase.</p>
    </section>
  </main>
</template>


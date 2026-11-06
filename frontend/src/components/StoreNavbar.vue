<script setup>
import { ChevronDown, KeyRound, LogOut, RefreshCcw, Search, Store, UserRound } from "lucide-vue-next";

const logoUrl = "/toktok-mark.svg";

defineProps({
  currentUser: { type: Object, required: true },
  myStore: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  searchQuery: { type: String, default: "" },
  accountMenuOpen: { type: Boolean, default: false },
});
const emit = defineEmits(["update:searchQuery", "update:accountMenuOpen", "refresh", "dashboard", "create-store", "change-password", "logout"]);
</script>

<template>
  <header class="site-header sticky top-0 z-30">
    <div class="mx-auto max-w-7xl px-5">
      <div class="grid gap-4 py-4 lg:grid-cols-[auto_minmax(260px,1fr)_auto] lg:items-center">
        <div class="flex items-center gap-3">
          <img :src="logoUrl" alt="Belanjoo" class="brand-logo" />
          <div class="min-w-0"><p class="text-lg font-semibold leading-6 text-ink">Belanjoo</p><p class="truncate text-xs font-medium text-[#68635d]">Curated goods for work and home</p></div>
        </div>

        <label class="relative block"><Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#68635d]" /><input :value="searchQuery" class="h-11 w-full border border-line bg-white pl-10 pr-4 text-sm outline-none transition focus:border-moss" placeholder="Search products, categories, or details" type="search" @input="emit('update:searchQuery', $event.target.value)" /></label>

        <div class="flex items-center justify-between gap-2 lg:justify-end">
          <button class="secondary-button h-11 px-3" :disabled="loading" title="Refresh data" @click="emit('refresh')"><RefreshCcw class="h-4 w-4" /><span class="hidden sm:inline">Refresh</span></button>
          <div class="relative">
            <button class="secondary-button h-11 px-3" title="Account" @click="emit('update:accountMenuOpen', !accountMenuOpen)"><UserRound class="h-4 w-4" /><span class="max-w-[120px] truncate">{{ currentUser.display_name }}</span><ChevronDown class="h-4 w-4 text-[#68635d]" /></button>
            <div v-if="accountMenuOpen" class="absolute right-0 top-12 z-40 w-56 border border-line bg-white p-2 shadow-panel" style="border-radius: 8px">
              <div class="border-b border-line px-3 py-2"><p class="truncate text-sm font-semibold">{{ currentUser.display_name }}</p><p class="truncate text-xs text-[#68635d]">{{ currentUser.username }}</p></div>
<button v-if="myStore" class="mt-2 flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-ink hover:bg-field" style="border-radius: 8px" @click="emit('dashboard')"><Store class="h-4 w-4 text-moss" />Store Dashboard</button>
<button v-else class="mt-2 flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-ink hover:bg-field" style="border-radius: 8px" @click="emit('create-store')"><Store class="h-4 w-4 text-moss" />Create Store</button>
              <button class="mt-1 flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-ink hover:bg-field" style="border-radius: 8px" @click="emit('change-password')"><KeyRound class="h-4 w-4 text-moss" />Change Password</button>
              <button class="mt-1 flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-ember hover:bg-[#f8eae5]" style="border-radius: 8px" @click="emit('logout')"><LogOut class="h-4 w-4" />Logout</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref } from "vue";
import { Store, X } from "lucide-vue-next";
import { request } from "../api";

const emit = defineEmits(["close", "created"]);

const busy = ref(false);
const error = ref("");
const form = ref({
  name: "",
  category: "",
  description: "",
  city: "",
  phone: "",
});

async function submit() {
  error.value = "";
  busy.value = true;
  try {
    const result = await request("/api/stores", {
      method: "POST",
      body: JSON.stringify({
        name: form.value.name,
        category: form.value.category,
        description: form.value.description,
        city: form.value.city,
        phone: form.value.phone,
      }),
    });
    emit("created", result);
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 grid place-items-center bg-black/45 p-5">
    <form class="w-full max-w-lg border border-line bg-white p-5 shadow-panel" style="border-radius: 8px" @submit.prevent="submit">
      <div class="flex items-start justify-between gap-4">
        <div class="flex items-center gap-3">
          <span class="grid h-10 w-10 shrink-0 place-items-center bg-[#1e3d2b] text-white" style="border-radius: 8px">
            <Store class="h-5 w-5" />
          </span>
          <div>
            <h2 class="text-lg font-semibold">Create Store</h2>
            <p class="mt-1 text-sm text-[#68635d]">Enter your store details to start selling on Belanjoo.</p>
          </div>
        </div>
        <button type="button" class="icon-button h-9 w-9" title="Close" @click="emit('close')">
          <X class="h-4 w-4" />
        </button>
      </div>

      <label class="mt-5 block text-sm font-medium text-[#4d4944]" for="store-name">Store name</label>
      <input
        id="store-name"
        v-model="form.name"
        class="mt-2 w-full border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss"
        style="border-radius: 8px"
        placeholder="Example: Sumber Rejeki Store"
        required
      />

      <label class="mt-4 block text-sm font-medium text-[#4d4944]" for="store-category">Store category</label>
      <input
        id="store-category"
        v-model="form.category"
        class="mt-2 w-full border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss"
        style="border-radius: 8px"
        placeholder="Example: Electronics, Fashion, Food"
        required
      />

      <label class="mt-4 block text-sm font-medium text-[#4d4944]" for="store-description">Store description</label>
      <textarea
        id="store-description"
        v-model="form.description"
        rows="3"
        class="mt-2 w-full resize-none border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss"
        style="border-radius: 8px"
        placeholder="Describe your products or store highlights"
        required
      ></textarea>

      <div class="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-[#4d4944]" for="store-city">City / address</label>
          <input
            id="store-city"
            v-model="form.city"
            class="mt-2 w-full border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss"
            style="border-radius: 8px"
            placeholder="Example: Bandung"
            required
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-[#4d4944]" for="store-phone">Store phone number</label>
          <input
            id="store-phone"
            v-model="form.phone"
            class="mt-2 w-full border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss"
            style="border-radius: 8px"
            placeholder="08xxxxxxxxxx"
            required
          />
        </div>
      </div>

      <p v-if="error" class="mt-4 border border-ember bg-[#f8eae5] px-3 py-2 text-sm text-ember" style="border-radius: 8px">
        {{ error }}
      </p>

      <div class="mt-5 flex justify-end gap-3">
        <button type="button" class="secondary-button" @click="emit('close')">Cancel</button>
        <button class="primary-button" :disabled="busy">
          <Store class="h-4 w-4" />
          Create Store
        </button>
      </div>
    </form>
  </div>
</template>

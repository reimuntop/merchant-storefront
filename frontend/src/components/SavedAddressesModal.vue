<script setup>
import { MapPin, Pencil, Plus, X } from "lucide-vue-next";
import { ref, watch } from "vue";

import { request } from "../api";

const props = defineProps({
  open: { type: Boolean, default: false },
});
const emit = defineEmits(["close"]);

const addresses = ref([]);
const loading = ref(false);
const saving = ref(false);
const error = ref("");
const editingId = ref(null);
const emptyForm = () => ({
  label: "",
  recipient_name: "",
  phone: "",
  address_line: "",
  city: "",
  postal_code: "",
  is_default: false,
});
const form = ref(emptyForm());

async function loadAddresses() {
  loading.value = true;
  error.value = "";
  try {
    addresses.value = await request("/api/me/addresses");
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function addAddress() {
  editingId.value = null;
  form.value = emptyForm();
}

function editAddress(address) {
  editingId.value = address.id;
  form.value = {
    label: address.label,
    recipient_name: address.recipient_name,
    phone: address.phone,
    address_line: address.address_line,
    city: address.city,
    postal_code: address.postal_code,
    is_default: address.is_default,
  };
}

async function saveAddress() {
  saving.value = true;
  error.value = "";
  try {
    const path = editingId.value
      ? `/api/me/addresses/${editingId.value}`
      : "/api/me/addresses";
    await request(path, {
      method: editingId.value ? "PATCH" : "POST",
      body: JSON.stringify(form.value),
    });
    await loadAddresses();
    addAddress();
  } catch (err) {
    error.value = err.message;
  } finally {
    saving.value = false;
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      addAddress();
      loadAddresses();
    }
  },
);
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 grid place-items-center bg-black/45 p-5">
    <section class="max-h-[90vh] w-full max-w-4xl overflow-y-auto border border-line bg-white p-5 shadow-panel" style="border-radius: 8px">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-lg font-semibold">Saved Addresses</h2>
          <p class="mt-1 text-sm text-[#68635d]">Manage delivery addresses for your account.</p>
        </div>
        <button type="button" class="icon-button h-9 w-9" title="Close" @click="emit('close')">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="mt-5 grid gap-5 md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <div>
          <div class="flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold">Address book</h3>
            <button type="button" class="secondary-button px-3 py-2" @click="addAddress">
              <Plus class="h-4 w-4" /> Add
            </button>
          </div>
          <p v-if="loading" class="mt-4 text-sm text-[#68635d]">Loading addresses...</p>
          <p v-else-if="!addresses.length" class="mt-4 border border-dashed border-line bg-field p-4 text-sm text-[#68635d]" style="border-radius: 8px">
            No saved addresses yet.
          </p>
          <div v-else class="mt-3 space-y-3">
            <button
              v-for="address in addresses"
              :key="address.id"
              type="button"
              class="flex w-full items-start gap-3 border p-3 text-left transition hover:border-moss"
              :class="editingId === address.id ? 'border-moss bg-field' : 'border-line bg-white'"
              style="border-radius: 8px"
              @click="editAddress(address)"
            >
              <MapPin class="mt-0.5 h-4 w-4 shrink-0 text-moss" />
              <span class="min-w-0 flex-1">
                <span class="flex items-center gap-2 text-sm font-semibold">
                  {{ address.label }}
                  <span v-if="address.is_default" class="text-xs font-medium text-moss">Default</span>
                </span>
                <span class="mt-1 block text-xs text-[#68635d]">{{ address.recipient_name }} · {{ address.phone }}</span>
                <span class="mt-1 block text-xs text-[#68635d]">{{ address.address_line }}, {{ address.city }} {{ address.postal_code }}</span>
              </span>
              <Pencil class="h-4 w-4 shrink-0 text-[#68635d]" />
            </button>
          </div>
        </div>

        <form class="border border-line bg-field p-4" style="border-radius: 8px" @submit.prevent="saveAddress">
          <h3 class="text-sm font-semibold">{{ editingId ? "Edit address" : "Add address" }}</h3>
          <div class="mt-4 grid gap-3 sm:grid-cols-2">
            <label class="text-sm font-medium text-[#4d4944]">Label<input v-model="form.label" required maxlength="80" class="mt-1 w-full border border-line bg-white px-3 py-2 text-sm outline-none focus:border-moss" placeholder="Home or Office" /></label>
            <label class="text-sm font-medium text-[#4d4944]">Recipient<input v-model="form.recipient_name" required maxlength="120" class="mt-1 w-full border border-line bg-white px-3 py-2 text-sm outline-none focus:border-moss" /></label>
            <label class="text-sm font-medium text-[#4d4944]">Phone<input v-model="form.phone" required maxlength="30" class="mt-1 w-full border border-line bg-white px-3 py-2 text-sm outline-none focus:border-moss" /></label>
            <label class="text-sm font-medium text-[#4d4944]">Postal code<input v-model="form.postal_code" required maxlength="20" class="mt-1 w-full border border-line bg-white px-3 py-2 text-sm outline-none focus:border-moss" /></label>
            <label class="text-sm font-medium text-[#4d4944] sm:col-span-2">Address<input v-model="form.address_line" required maxlength="300" class="mt-1 w-full border border-line bg-white px-3 py-2 text-sm outline-none focus:border-moss" /></label>
            <label class="text-sm font-medium text-[#4d4944] sm:col-span-2">City<input v-model="form.city" required maxlength="120" class="mt-1 w-full border border-line bg-white px-3 py-2 text-sm outline-none focus:border-moss" /></label>
          </div>
          <label class="mt-4 flex items-center gap-2 text-sm font-medium text-[#4d4944]"><input v-model="form.is_default" type="checkbox" /> Use as default address</label>
          <p v-if="error" class="mt-4 border border-ember bg-[#f8eae5] px-3 py-2 text-sm text-ember" style="border-radius: 8px">{{ error }}</p>
          <div class="mt-5 flex justify-end gap-3">
            <button type="button" class="secondary-button" @click="addAddress">Clear</button>
            <button class="primary-button" :disabled="saving">{{ saving ? "Saving..." : "Save Address" }}</button>
          </div>
        </form>
      </div>
    </section>
  </div>
</template>

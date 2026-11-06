<script setup>
import { ref } from "vue";
import { CheckCircle2, History, Package, X } from "lucide-vue-next";
import { request } from "../api";
import { formatIDR } from "../formatters";

defineProps({ purchases: { type: Array, required: true } });
const open = ref(false);
const refundPurchase = ref(null);
const refundAmount = ref("");
const refundReason = ref("");
const refundBusy = ref(false);
const refundError = ref("");
const refundNotice = ref("");
const submittedRefunds = ref({});
const returnPurchase = ref(null);
const returnQuantity = ref("1");
const returnReason = ref("");
const returnBusy = ref(false);
const returnError = ref("");
const returnNotice = ref("");
const submittedReturns = ref({});

function refundFor(purchase) {
  return submittedRefunds.value[purchase.id] || purchase.refund;
}

function openRefund(purchase) {
  refundPurchase.value = purchase;
  refundAmount.value = String(purchase.total);
  refundReason.value = "";
  refundError.value = "";
  refundNotice.value = "";
}

function closeRefund() {
  if (refundBusy.value) return;
  refundPurchase.value = null;
}

async function submitRefund() {
  refundBusy.value = true;
  refundError.value = "";
  try {
    const refund = await request(`/api/purchases/${refundPurchase.value.id}/refund`, {
      method: "POST",
      body: JSON.stringify({
        reason: refundReason.value.trim(),
        refund_amount: Number(refundAmount.value),
      }),
    });
    submittedRefunds.value[refund.purchase_id] = refund;
    refundNotice.value = `Refund request #${refund.id} submitted.`;
    refundPurchase.value = null;
  } catch (err) {
    refundError.value = err.message;
  } finally {
    refundBusy.value = false;
  }
}

function returnFor(purchase) {
  return submittedReturns.value[purchase.id] || purchase.return_request;
}

function openReturn(purchase) {
  returnPurchase.value = purchase;
  returnQuantity.value = "1";
  returnReason.value = "";
  returnError.value = "";
  returnNotice.value = "";
}

function closeReturn() {
  if (returnBusy.value) return;
  returnPurchase.value = null;
}

async function submitReturn() {
  returnBusy.value = true;
  returnError.value = "";
  try {
    const itemReturn = await request(`/api/purchases/${returnPurchase.value.id}/returns`, {
      method: "POST",
      body: JSON.stringify({
        quantity: Number(returnQuantity.value),
        reason: returnReason.value.trim(),
      }),
    });
    submittedReturns.value[itemReturn.purchase_id] = itemReturn;
    returnNotice.value = `Return request #${itemReturn.id} submitted.`;
    returnPurchase.value = null;
  } catch (err) {
    returnError.value = err.message;
  } finally {
    returnBusy.value = false;
  }
}
</script>

<template>
  <button
    v-if="!open"
    class="fixed bottom-44 right-5 z-40 grid h-12 w-12 place-items-center rounded-2xl bg-white text-ink shadow-[0_12px_30px_rgba(20,45,29,0.16)] ring-1 ring-[#e4ece5] transition hover:-translate-y-1"
    title="Purchase history"
    @click="open = true"
  >
    <History class="h-5 w-5 text-forest" />
  </button>
  <section
    v-else
    class="fixed bottom-44 right-5 z-40 flex h-[min(560px,calc(100vh-180px))] w-[min(390px,calc(100vw-40px))] flex-col overflow-hidden rounded-[22px] border border-white bg-white shadow-[0_20px_60px_rgba(20,45,29,0.2)]"
  >
    <header
      class="flex items-center justify-between bg-[#163021] px-5 py-4 text-white"
    >
      <div class="flex items-center gap-3">
        <div class="grid h-10 w-10 place-items-center rounded-xl bg-white/10">
          <History class="h-5 w-5" />
        </div>
        <div>
          <h2 class="font-semibold">Purchase history</h2>
          <p class="text-xs text-white/70">Your completed orders</p>
        </div>
      </div>
      <button
        class="grid h-9 w-9 place-items-center rounded-xl hover:bg-white/10"
        title="Close history"
        @click="open = false"
      >
        <X class="h-5 w-5" />
      </button>
    </header>
    <p v-if="refundNotice" class="mx-4 mt-4 rounded-xl bg-[#e9f1e9] px-3 py-2 text-xs font-medium text-[#1e3d2b]">
      {{ refundNotice }}
    </p>
    <p v-if="returnNotice" class="mx-4 mt-4 rounded-xl bg-[#e9f1e9] px-3 py-2 text-xs font-medium text-[#1e3d2b]">
      {{ returnNotice }}
    </p>
    <div
      v-if="!purchases.length"
      class="grid flex-1 place-items-center p-6 text-center"
    >
      <div>
        <div
          class="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[#f4efe6] text-[#1e3d2b]"
        >
          <Package class="h-6 w-6" />
        </div>
        <h3 class="mt-4 font-semibold">No purchases yet</h3>
        <p class="mt-1 text-sm text-[#1e3d2b]">
          Completed orders will appear here.
        </p>
      </div>
    </div>
    <div v-else class="flex-1 space-y-3 overflow-y-auto bg-[#ffffff] p-4">
      <article
        v-for="purchase in purchases"
        :key="purchase.id"
        class="rounded-2xl border border-line bg-white p-4"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex min-w-0 gap-3">
            <div
              class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#f4efe6] text-[#1e3d2b]"
            >
              <Package class="h-4 w-4" />
            </div>
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold">
                {{ purchase.product.name }}
              </p>
              <p class="mt-1 text-xs text-[#1e3d2b]">
                Qty {{ purchase.quantity }} · Order #{{ purchase.id }}
              </p>
            </div>
          </div>
          <p class="whitespace-nowrap text-sm font-bold text-forest">
            {{ formatIDR(purchase.total) }}
          </p>
        </div>
        <div
          class="mt-3 flex items-center justify-between border-t border-line pt-3 text-xs"
        >
          <span
            class="inline-flex items-center gap-1 rounded-full bg-[#f4efe6] px-2.5 py-1 font-semibold capitalize text-[#1e3d2b]"
            ><CheckCircle2 class="h-3.5 w-3.5" />{{
              purchase.status || "completed"
            }}</span
          ><span class="text-[#8b948d]">{{
            purchase.discount_code ? `Discount ${purchase.discount_code}` : ""
          }}</span>
        </div>
        <div class="mt-3 flex flex-wrap justify-end gap-2">
          <span v-if="returnFor(purchase)" class="self-center text-xs font-semibold capitalize text-[#8b948d]">
            Return {{ returnFor(purchase).status }}
          </span>
          <button
            v-else
            type="button"
            class="rounded-xl border border-[#1e3d2b] px-3 py-1.5 text-xs font-semibold text-[#1e3d2b] transition hover:bg-[#e9f1e9]"
            @click="openReturn(purchase)"
          >
            Return Item
          </button>
          <span v-if="refundFor(purchase)" class="text-xs font-semibold capitalize text-[#8b948d]">
            Refund {{ refundFor(purchase).status }}
          </span>
          <button
            v-else
            type="button"
            class="rounded-xl border border-[#1e3d2b] px-3 py-1.5 text-xs font-semibold text-[#1e3d2b] transition hover:bg-[#e9f1e9]"
            @click="openRefund(purchase)"
          >
            Request Refund
          </button>
        </div>
      </article>
    </div>
  </section>

  <div v-if="refundPurchase" class="fixed inset-0 z-50 grid place-items-center bg-black/45 p-5">
    <form class="w-full max-w-md rounded-2xl bg-white p-5 shadow-panel" @submit.prevent="submitRefund">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-lg font-semibold">Request Refund</h2>
          <p class="mt-1 text-sm text-[#68635d]">Order #{{ refundPurchase.id }} · {{ refundPurchase.product.name }}</p>
        </div>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-xl hover:bg-[#f3f4f3]" title="Close" @click="closeRefund">
          <X class="h-4 w-4" />
        </button>
      </div>

      <label class="mt-5 block text-sm font-medium">
        Refund amount
        <input
          v-model="refundAmount"
          type="number"
          min="0.01"
          step="0.01"
          required
          class="mt-2 w-full rounded-xl border border-line px-3 py-2"
        />
      </label>
      <label class="mt-4 block text-sm font-medium">
        Reason
        <textarea
          v-model="refundReason"
          required
          maxlength="1000"
          rows="4"
          class="mt-2 w-full rounded-xl border border-line px-3 py-2"
          placeholder="Describe why you are requesting a refund"
        ></textarea>
      </label>
      <p v-if="refundError" class="mt-3 text-sm text-red-700">{{ refundError }}</p>
      <div class="mt-5 flex justify-end gap-3">
        <button type="button" class="rounded-xl border border-line px-4 py-2 text-sm font-semibold" :disabled="refundBusy" @click="closeRefund">
          Cancel
        </button>
        <button type="submit" class="rounded-xl bg-[#163021] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" :disabled="refundBusy">
          {{ refundBusy ? "Submitting..." : "Submit Refund" }}
        </button>
      </div>
    </form>
  </div>

  <div v-if="returnPurchase" class="fixed inset-0 z-50 grid place-items-center bg-black/45 p-5">
    <form class="w-full max-w-md rounded-2xl bg-white p-5 shadow-panel" @submit.prevent="submitReturn">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-lg font-semibold">Return Item</h2>
          <p class="mt-1 text-sm text-[#68635d]">Order #{{ returnPurchase.id }} Â· {{ returnPurchase.product.name }}</p>
          <p class="mt-1 text-xs text-[#8b948d]">Purchased quantity: {{ returnPurchase.quantity }}</p>
        </div>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-xl hover:bg-[#f3f4f3]" title="Close" @click="closeReturn">
          <X class="h-4 w-4" />
        </button>
      </div>

      <label class="mt-5 block text-sm font-medium">
        Quantity
        <input
          v-model="returnQuantity"
          type="number"
          min="1"
          step="1"
          required
          class="mt-2 w-full rounded-xl border border-line px-3 py-2"
        />
      </label>
      <label class="mt-4 block text-sm font-medium">
        Reason
        <textarea
          v-model="returnReason"
          required
          maxlength="1000"
          rows="4"
          class="mt-2 w-full rounded-xl border border-line px-3 py-2"
          placeholder="Describe why you are returning this item"
        ></textarea>
      </label>
      <p v-if="returnError" class="mt-3 text-sm text-red-700">{{ returnError }}</p>
      <div class="mt-5 flex justify-end gap-3">
        <button type="button" class="rounded-xl border border-line px-4 py-2 text-sm font-semibold" :disabled="returnBusy" @click="closeReturn">
          Cancel
        </button>
        <button type="submit" class="rounded-xl bg-[#163021] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" :disabled="returnBusy">
          {{ returnBusy ? "Submitting..." : "Submit Return" }}
        </button>
      </div>
    </form>
  </div>
</template>

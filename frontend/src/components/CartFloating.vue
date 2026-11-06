<script setup>
import { computed, ref, watch } from "vue";
import { ArrowRight, Minus, ShoppingCart, Tag, X } from "lucide-vue-next";
import { formatIDR } from "../formatters";
import { request } from "../api";

const props = defineProps({
  cart: { type: Array, required: true },
  cartTotal: { type: Number, required: true },
  cartCount: { type: Number, required: true },
  discountCode: { type: String, default: "" },
  loading: { type: Boolean, default: false },
  checkoutError: { type: String, default: "" },
});
const emit = defineEmits(["remove", "checkout", "update:discountCode"]);
const open = ref(false);
const hasItems = computed(() => props.cart.length > 0);
const addresses = ref([]);
const checkoutState = ref(null);
const addressError = ref("");
const shippingFee = computed(() => checkoutState.value?.shipping_fee || 0);
const checkoutTotal = computed(() => props.cartTotal + shippingFee.value);

async function loadShippingDetails() {
  addressError.value = "";
  try {
    const [addressRows, state] = await Promise.all([
      request("/api/me/addresses"),
      request("/api/cart/shipping-address"),
    ]);
    addresses.value = addressRows;
    checkoutState.value = state;
  } catch (err) {
    addressError.value = err.message || "Shipping details could not be loaded.";
  }
}

async function selectShippingAddress(event) {
  const addressId = Number(event.target.value);
  if (!addressId) return;
  addressError.value = "";
  try {
    checkoutState.value = await request("/api/cart/shipping-address", {
      method: "PATCH",
      body: JSON.stringify({ address_id: addressId }),
    });
  } catch (err) {
    addressError.value = err.message || "Shipping address could not be selected.";
  }
}

watch([open, hasItems], ([isOpen, cartHasItems]) => {
  if (isOpen && cartHasItems) loadShippingDetails();
});
</script>

<template>
  <button
    v-if="!open"
    class="fixed bottom-24 right-5 z-40 grid h-14 w-14 place-items-center rounded-2xl bg-forest text-white shadow-[0_14px_35px_rgba(20,45,29,0.2)] transition hover:bg-[#1e3d2b]"
    title="Open cart"
    @click="open = true"
  >
    <ShoppingCart class="h-6 w-6" /><span
      class="absolute -right-2 -top-2 grid h-6 min-w-6 place-items-center rounded-full bg-ember px-1 text-[10px] font-bold text-white"
      >{{ cartCount }}</span
    >
  </button>

  <section
    v-else
    class="fixed bottom-24 right-5 z-50 flex h-[min(620px,calc(100vh-150px))] w-[min(410px,calc(100vw-40px))] flex-col overflow-hidden rounded-[22px] border border-white bg-white shadow-[0_20px_60px_rgba(20,45,29,0.2)]"
  >
    <header
      class="flex items-center justify-between bg-forest px-5 py-4 text-white"
    >
      <div class="flex items-center gap-3">
        <div class="grid h-10 w-10 place-items-center rounded-xl bg-white/15">
          <ShoppingCart class="h-5 w-5" />
        </div>
        <div>
          <h2 class="font-semibold">Shopping cart</h2>
          <p class="text-xs text-white/70">
            {{ cartCount }} items ready to checkout
          </p>
        </div>
      </div>
      <button
        class="grid h-9 w-9 place-items-center rounded-xl hover:bg-white/10"
        title="Close cart"
        @click="open = false"
      >
        <X class="h-5 w-5" />
      </button>
    </header>
    <div
      v-if="!hasItems"
      class="grid flex-1 place-items-center p-6 text-center"
    >
      <div>
        <div
          class="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[#f4efe6] text-[#b3261e]"
        >
          <ShoppingCart class="h-6 w-6" />
        </div>
        <h3 class="mt-4 font-semibold">Your cart is empty</h3>
        <p class="mt-1 text-sm text-[#1e3d2b]">
          Add products to your cart to start checkout.
        </p>
      </div>
    </div>
    <div v-else class="flex min-h-0 flex-1 flex-col">
      <div class="flex-1 space-y-3 overflow-y-auto bg-[#ffffff] p-4">
        <div
          v-for="item in cart"
          :key="item.id"
          class="flex gap-3 rounded-2xl border border-line bg-white p-3"
        >
          <img
            :src="item.product.image_url"
            :alt="item.product.name"
            class="h-16 w-16 rounded-xl object-cover"
          />
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-semibold">
              {{ item.product.name }}
            </p>
            <p v-if="item.variant" class="mt-1 text-xs text-[#1e3d2b]">
              {{ item.variant.name }} · {{ item.variant.sku }}
            </p>
            <p class="mt-2 text-xs text-[#1e3d2b]">
              Qty {{ item.quantity }} ·
              <span class="font-bold text-forest">{{
                formatIDR(item.line_total)
              }}</span>
            </p>
          </div>
          <button
            class="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-[#9aa49d] hover:bg-[#f8eae5] hover:text-ember"
            title="Remove item"
            @click="emit('remove', item.product.id, item.variant?.id)"
          >
            <Minus class="h-4 w-4" />
          </button>
        </div>
      </div>
      <div class="border-t border-line bg-white p-4">
        <label class="mb-3 block text-sm text-[#4d4944]">
          Shipping address
          <select
            class="mt-1 w-full border border-line bg-field px-3 py-2 text-sm"
            :value="checkoutState?.shipping_address_id || ''"
            @change="selectShippingAddress"
          >
            <option value="" disabled>Select a saved address</option>
            <option v-for="address in addresses" :key="address.id" :value="address.id">
              {{ address.label }} · {{ address.city }}
            </option>
          </select>
        </label>
        <p v-if="addressError" class="mb-3 text-xs text-ember">{{ addressError }}</p>
        <div class="mb-3 flex items-center justify-between text-sm">
          <span class="text-[#1e3d2b]">Subtotal</span
          ><span class="text-lg font-bold text-ink">{{
            formatIDR(cartTotal)
          }}</span>
        </div>
        <div class="mb-3 flex items-center justify-between text-sm">
          <span class="text-[#1e3d2b]">Shipping Fee</span>
          <span class="font-semibold text-ink">{{ formatIDR(shippingFee) }}</span>
        </div>
        <div class="mb-3 flex items-center justify-between border-t border-line pt-3 text-sm">
          <span class="font-semibold text-ink">Total</span>
          <span class="text-lg font-bold text-ink">{{ formatIDR(checkoutTotal) }}</span>
        </div>
        <div class="relative">
          <Tag
            class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8b948d]"
          /><input
            :value="discountCode"
            class="w-full border border-line bg-field py-2.5 pl-9 pr-3 text-sm"
            placeholder="Discount code (optional)"
            maxlength="40"
            @input="emit('update:discountCode', $event.target.value)"
          />
        </div>
        <p
          v-if="checkoutError"
          class="mt-2 rounded-lg border border-ember bg-[#f8eae5] px-3 py-2 text-xs font-medium text-ember"
        >
          {{ checkoutError }}
        </p>
        <button
          class="primary-button mt-3 w-full py-3"
          :disabled="loading"
          @click="emit('checkout')"
        >
          Checkout <ArrowRight class="h-4 w-4" />
        </button>
      </div>
    </div>
  </section>
</template>

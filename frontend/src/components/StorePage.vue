<script setup>
import { ref } from "vue";
import { ArrowLeft, Clock3, MapPin, RotateCcw, Star, Store as StoreIcon } from "lucide-vue-next";
import CartFloating from "./CartFloating.vue";
import ProductCard from "./ProductCard.vue";
import PurchaseHistoryFloating from "./PurchaseHistoryFloating.vue";
import StoreNavbar from "./StoreNavbar.vue";
import { assetUrl } from "../api";

const props = defineProps({
  storeData: { type: Object, required: true },
  user: { type: Object, required: true },
  myStore: { type: Object, default: null },
  cart: { type: Array, required: true },
  cartTotal: { type: Number, required: true },
  cartCount: { type: Number, required: true },
  discountCode: { type: String, default: "" },
  checkoutError: { type: String, default: "" },
  purchases: { type: Array, required: true },
  loading: { type: Boolean, default: false },
});
const emit = defineEmits(["back", "open-product", "add", "changed", "dashboard", "create-store", "change-password", "logout", "remove-cart", "checkout", "update:discountCode"]);
const searchQuery = ref("");
const accountMenuOpen = ref(false);

function storeBackgroundStyle() {
  const banner = assetUrl(props.storeData.store.banner_url);
  if (!banner) return {};
  return {
    backgroundImage: `linear-gradient(rgba(246, 251, 247, 0.82), rgba(246, 251, 247, 0.94)), url("${banner}")`,
    backgroundPosition: "center",
    backgroundSize: "cover",
    backgroundAttachment: "fixed",
  };
}
</script>

<template>
  <main class="app-shell min-h-screen" :style="storeBackgroundStyle()">
    <StoreNavbar :current-user="user" :my-store="myStore" :loading="loading" :search-query="searchQuery" :account-menu-open="accountMenuOpen" @update:search-query="searchQuery = $event" @update:account-menu-open="accountMenuOpen = $event" @refresh="emit('changed')" @dashboard="emit('dashboard')" @create-store="emit('create-store')" @change-password="emit('change-password')" @logout="emit('logout')" />

    <section class="mx-auto max-w-7xl px-5 py-7 sm:py-10">
      <button class="secondary-button mb-5" @click="emit('back')"><ArrowLeft class="h-4 w-4" />Back to shop</button>
      <section class="overflow-hidden rounded-[24px] border border-white/80 bg-white shadow-[0_18px_50px_rgba(20,45,29,0.1)]">
        <div class="relative h-40 overflow-hidden bg-[#163021] sm:h-52">
          <img v-if="storeData.store.banner_url" :src="assetUrl(storeData.store.banner_url)" :alt="storeData.store.name" class="h-full w-full object-cover opacity-80" />
          <div class="absolute inset-0 bg-gradient-to-t from-[#142a1d]/80 via-transparent to-transparent"></div>
        </div>
        <div class="relative px-5 pb-6 sm:px-8">
          <div class="-mt-12 flex flex-col gap-4 sm:-mt-14 sm:flex-row sm:items-end sm:justify-between">
            <div class="flex items-end gap-4">
              <div class="grid h-24 w-24 place-items-center overflow-hidden rounded-2xl border-4 border-white bg-[#f4efe6] text-[#1e3d2b] shadow-lg sm:h-28 sm:w-28">
                <img v-if="storeData.store.logo_url" :src="assetUrl(storeData.store.logo_url)" :alt="storeData.store.name" class="h-full w-full object-cover" />
                <StoreIcon v-else class="h-9 w-9" />
              </div>
              <div class="pb-1"><h1 class="text-2xl font-semibold tracking-tight sm:text-3xl">{{ storeData.store.name }}</h1><p class="mt-1 text-sm text-[#1e3d2b]">{{ storeData.store.category }} · {{ storeData.store.city }}</p></div>
            </div>
            <div class="flex items-center gap-2 rounded-2xl bg-[#f4efe6] px-4 py-3"><Star class="h-5 w-5 fill-[#f0b429] text-[#f0b429]" /><div><p class="font-bold text-ink">{{ storeData.average_rating || "—" }}</p><p class="text-xs text-[#1e3d2b]">{{ storeData.review_count }} reviews</p></div></div>
          </div>
          <p class="mt-6 max-w-3xl text-sm leading-6 text-[#536158]">{{ storeData.store.description }}</p>
          <div class="mt-5 grid gap-3 border-t border-line pt-5 text-sm text-[#5c5a50] sm:grid-cols-3"><div class="flex gap-2"><MapPin class="h-4 w-4 shrink-0 text-[#1e3d2b]" />{{ storeData.store.address || storeData.store.city }}</div><div class="flex gap-2"><Clock3 class="h-4 w-4 shrink-0 text-[#1e3d2b]" />{{ storeData.store.opening_hours || "Opening hours unavailable" }}</div><div class="flex gap-2"><RotateCcw class="h-4 w-4 shrink-0 text-[#1e3d2b]" />{{ storeData.store.return_policy || "Return policy unavailable" }}</div></div>
        </div>
      </section>

    <section class="mt-8"><div class="flex items-end justify-between gap-4"><div><p class="text-moss">Store catalog</p><h2 class="mt-2 text-2xl font-semibold tracking-tight">Products from {{ storeData.store.name }}</h2></div><p class="text-sm text-[#1e3d2b]">{{ storeData.products.length }} products</p></div><div v-if="storeData.products.length" class="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-4 xl:grid-cols-5"><ProductCard v-for="product in storeData.products" :key="product.id" :product="product" @select="emit('open-product', product)" @add="emit('add', product)" /></div><div v-else class="mt-5 rounded-2xl border border-dashed border-line p-10 text-center text-sm text-[#1e3d2b]">No active products in this store yet.</div></section>
    </section>

    <CartFloating :cart="cart" :cart-total="cartTotal" :cart-count="cartCount" :discount-code="discountCode" :checkout-error="checkoutError" :loading="loading" @remove="(...args) => emit('remove-cart', ...args)" @checkout="emit('checkout')" @update:discount-code="emit('update:discountCode', $event)" />
    <PurchaseHistoryFloating :purchases="purchases" />
  </main>
</template>

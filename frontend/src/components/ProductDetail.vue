<script setup>
import { computed, ref, watch } from "vue";
import { ArrowLeft, Check, Package, ShoppingCart, Store, Tag, Zap } from "lucide-vue-next";
import CartFloating from "./CartFloating.vue";
import PurchaseHistoryFloating from "./PurchaseHistoryFloating.vue";
import ProductCard from "./ProductCard.vue";
import ReviewPanel from "./ReviewPanel.vue";
import StoreNavbar from "./StoreNavbar.vue";
import { formatIDR } from "../formatters";
import { request } from "../api";

const props = defineProps({
  product: { type: Object, required: true },
  userId: { type: Number, required: true },
  user: { type: Object, default: null },
  canReview: { type: Boolean, default: false },
  products: { type: Array, default: () => [] },
  myStore: { type: Object, default: null },
  cartTotal: { type: Number, default: 0 },
  cartCount: { type: Number, default: 0 },
  cart: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  discountCode: { type: String, default: "" },
  checkoutError: { type: String, default: "" },
  purchases: { type: Array, default: () => [] },
});
const emit = defineEmits([
  "back",
  "add",
  "changed",
  "open-product",
  "open-store",
  "dashboard",
  "create-store",
  "change-password",
  "logout",
  "cart",
  "remove-cart",
  "checkout",
  "update:discountCode",
]);
const selectedVariant = ref(props.product.variants?.[0] || null);
const detailSearchQuery = ref("");
const detailMenuOpen = ref(false);
const questions = ref([]);
const questionMessage = ref("");
const questionBusy = ref(false);
const questionError = ref("");
const claimBusy = ref(false);
const claimError = ref("");
const claimNotice = ref("");
const claimRemaining = ref(props.product.stock);

watch(() => props.product.id, async (productId) => {
  questions.value = [];
  questionMessage.value = "";
  questionError.value = "";
  claimError.value = "";
  claimNotice.value = "";
  claimRemaining.value = props.product.stock;
  try {
    const rows = await request(`/api/products/${productId}/questions`);
    if (props.product.id === productId) questions.value = rows;
  } catch (err) {
    if (props.product.id === productId) questionError.value = err.message;
  }
}, { immediate: true });

const limitedClaimEligible = computed(
  () =>
    !props.product.variants?.length &&
    props.product.stock !== null &&
    props.product.stock !== undefined,
);
const claimSoldOut = computed(
  () => claimRemaining.value !== null && claimRemaining.value <= 0,
);

async function claimProduct() {
  if (claimBusy.value || claimSoldOut.value) return;
  claimBusy.value = true;
  claimError.value = "";
  claimNotice.value = "";
  try {
    const result = await request(`/api/products/${props.product.id}/claim`, {
      method: "POST",
    });
    claimRemaining.value = result.remaining_stock;
    claimNotice.value = "Product successfully claimed.";
    emit("changed");
  } catch (err) {
    claimError.value = err.message;
  } finally {
    claimBusy.value = false;
  }
}

async function askQuestion() {
  if (!questionMessage.value.trim() || questionBusy.value) return;
  questionBusy.value = true;
  questionError.value = "";
  const productId = props.product.id;
  try {
    const question = await request(`/api/products/${productId}/questions`, {
      method: "POST",
      body: JSON.stringify({ message: questionMessage.value }),
    });
    if (props.product.id === productId) {
      questions.value.unshift(question);
      questionMessage.value = "";
    }
  } catch (err) {
    questionError.value = err.message;
  } finally {
    questionBusy.value = false;
  }
}

const currentPrice = computed(
  () => selectedVariant.value?.price ?? props.product.price,
);
const currentStock = computed(() =>
  selectedVariant.value ? selectedVariant.value.stock : props.product.stock,
);
const unavailable = computed(
  () =>
    props.product.status === "out-of-stock" ||
    (currentStock.value !== null &&
      currentStock.value !== undefined &&
      currentStock.value <= 0),
);
const similarProducts = computed(() =>
  props.products
    .filter(
      (item) =>
        item.id !== props.product.id &&
        item.category === props.product.category,
    )
    .slice(0, 4),
);

function selectVariant(variant) {
  selectedVariant.value = variant;
}

function removeCart(...args) {
  emit("remove-cart", ...args);
}
</script>

<template>
  <main class="app-shell min-h-screen">
    <StoreNavbar
      :current-user="user"
      :my-store="myStore"
      :loading="loading"
      :search-query="detailSearchQuery"
      :account-menu-open="detailMenuOpen"
      @update:search-query="detailSearchQuery = $event"
      @update:account-menu-open="detailMenuOpen = $event"
      @refresh="emit('changed')"
      @dashboard="emit('dashboard')"
      @create-store="emit('create-store')"
      @change-password="emit('change-password')"
      @logout="emit('logout')"
    />

    <section class="mx-auto max-w-7xl px-5 py-7 sm:py-10">
      <div class="mb-5">
        <button class="secondary-button" @click="emit('back')">
          <ArrowLeft class="h-4 w-4" />Back to shop
        </button>
      </div>
      <div
        class="grid gap-7 lg:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)]"
      >
        <div
          class="overflow-hidden rounded-[24px] border border-white/80 bg-white/80 p-2 shadow-[0_18px_50px_rgba(20,45,29,0.1)]"
        >
          <div
            class="relative aspect-[4/3] overflow-hidden rounded-[18px] bg-field"
          >
            <img
              :src="product.image_url"
              :alt="product.name"
              class="h-full w-full object-cover"
            />
            <span
              class="absolute left-5 top-5 rounded-full bg-white/90 px-3 py-1.5 text-xs font-bold text-[#1e3d2b] shadow-sm"
              >{{ product.category }}</span
            >
          </div>
        </div>

        <div class="flex flex-col justify-center">
          <p class="text-xs text-[#1e3d2b]">
            {{ product.category }}
          </p>
          <button
            v-if="product.store"
            class="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-[#68635d] hover:text-[#1e3d2b]"
            @click="emit('open-store', product.store.slug)"
          >
            <Store class="h-4 w-4" /> {{ product.store.name }}
          </button>
          <h1
            class="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
          >
            {{ product.name }}
          </h1>
          <p
            v-if="product.sku"
            class="mt-3 text-xs font-medium text-[#8b948d]"
          >
            SKU {{ product.sku }}
          </p>
          <p class="mt-5 text-3xl font-bold text-[#1e3d2b] sm:text-4xl">
            {{ formatIDR(currentPrice) }}
          </p>
          <p class="mt-5 max-w-xl text-base leading-7 text-[#5e6860]">
            {{ product.description }}
          </p>

          <div v-if="limitedClaimEligible" class="mt-6 rounded-2xl border border-amber-300 bg-amber-50 p-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p class="inline-flex items-center gap-2 text-amber-800">
                  <Zap class="h-4 w-4" /> Flash Sale
                </p>
                <p class="mt-1 text-sm font-semibold text-ink">
                  {{ claimSoldOut ? "Sold out" : `Only ${claimRemaining} remaining` }}
                </p>
              </div>
              <button
                type="button"
                class="rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-700 disabled:cursor-not-allowed disabled:opacity-60"
                :disabled="claimBusy || claimSoldOut"
                @click="claimProduct"
              >
                {{ claimBusy ? "Claiming..." : claimSoldOut ? "No longer available" : "Claim Now" }}
              </button>
            </div>
            <p v-if="claimNotice" class="mt-3 text-sm font-medium text-green-700">{{ claimNotice }}</p>
            <p v-if="claimError" class="mt-3 text-sm font-medium text-red-700">{{ claimError }}</p>
          </div>

          <div v-if="product.variants?.length" class="mt-7">
            <div class="mb-3 flex items-center justify-between">
              <p class="text-sm font-bold text-ink">Choose a variant</p>
              <p class="text-xs text-[#7c877f]">
                {{ product.variants.length }} options
              </p>
            </div>
            <div class="grid gap-2 sm:grid-cols-2">
              <button
                v-for="variant in product.variants"
                :key="variant.id"
                class="flex items-center justify-between rounded-xl border px-3 py-3 text-left transition"
                :class="
                  selectedVariant?.id === variant.id
                    ? 'border-moss bg-[#f4efe6] text-[#1e3d2b] shadow-sm'
                    : 'border-line bg-white hover:border-moss'
                "
                :disabled="!variant.active || variant.stock <= 0"
                @click="selectVariant(variant)"
              >
                <span
                  ><span class="block text-sm font-semibold">{{
                    variant.name
                  }}</span
                  ><span class="mt-1 block text-xs text-[#7c877f]"
                    >{{ variant.size || ""
                    }}{{ variant.size && variant.color ? " · " : ""
                    }}{{ variant.color || "" }} · {{ variant.sku }}</span
                  ></span
                >
                <Check
                  v-if="selectedVariant?.id === variant.id"
                  class="h-4 w-4"
                />
              </button>
            </div>
          </div>

          <div class="mt-7 flex flex-wrap items-center gap-3">
            <button
              class="primary-button px-5 py-3"
              :disabled="unavailable"
              @click="emit('add', product, selectedVariant?.id)"
            >
              <ShoppingCart class="h-4 w-4" />{{
                unavailable ? "Out of stock" : "Add to cart"
              }}</button
            ><span
              class="inline-flex items-center gap-2 rounded-full bg-[#eef5ef] px-3 py-2 text-xs font-semibold text-[#1e3d2b] shadow-sm"
              ><Package class="h-4 w-4" />{{
                unavailable
                  ? "Currently unavailable"
                  : `${currentStock ?? "Available"} in stock`
              }}</span
            >
          </div>
          <div
            class="mt-7 grid gap-3 border-t border-line pt-5 text-sm text-[#5c5a50] sm:grid-cols-2"
          >
            <div class="flex gap-2">
              <Tag class="h-4 w-4 shrink-0 text-moss" /><span
                >Verified product listing</span
              >
            </div>
            <div class="flex gap-2">
              <Check class="h-4 w-4 shrink-0 text-moss" /><span
                >Secure checkout</span
              >
            </div>
          </div>
        </div>
      </div>

      <section class="mt-8 border border-line bg-white p-5">
        <h2 class="text-xl font-semibold">Product Questions</h2>
        <p class="mt-1 text-sm text-[#5c5a50]">Ask the seller about this product.</p>
        <form class="mt-4 space-y-3" @submit.prevent="askQuestion">
          <textarea v-model="questionMessage" class="w-full border border-line p-3" rows="3" maxlength="5000" required aria-label="Your product question" placeholder="Apakah produk ini tersedia warna hitam?" />
          <button class="primary-button" :disabled="questionBusy || !questionMessage.trim()">{{ questionBusy ? 'Sending…' : 'Ask Question' }}</button>
        </form>
        <p v-if="questionError" class="mt-3 text-sm text-red-600">{{ questionError }}</p>
        <div class="mt-5 space-y-4">
          <article v-for="question in questions" :key="question.id" class="border-t border-line pt-4">
            <p class="text-xs text-[#5c5a50]">{{ question.customer_name }} · {{ question.created_at.slice(0, 10) }}</p>
            <p class="mt-2 whitespace-pre-wrap">{{ question.message }}</p>
            <div v-if="question.answered_at" class="mt-3 bg-[#eef5ef] p-3">
              <p class="text-xs font-semibold text-moss">Seller answer</p>
              <p class="mt-1 whitespace-pre-wrap">{{ question.answer }}</p>
            </div>
            <p v-else class="mt-2 text-xs text-[#5c5a50]">Awaiting seller answer</p>
          </article>
          <p v-if="!questions.length" class="text-sm text-[#5c5a50]">No questions yet. Be the first to ask.</p>
        </div>
      </section>

      <ReviewPanel
        class="mt-8"
        :product="product"
        :user-id="userId"
        :can-review="canReview"
        @changed="emit('changed')"
      />

      <section
        v-if="similarProducts.length"
        class="mt-10 border-t border-line pt-8"
      >
        <div class="flex items-end justify-between gap-4">
          <div>
            <p class="text-moss">
              You may also like
            </p>
            <h2 class="mt-2 text-2xl font-semibold tracking-tight">
              Similar products
            </h2>
          </div>
          <p class="hidden text-sm text-[#7c877f] sm:block">
            More products from the same category
          </p>
        </div>
        <div class="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <ProductCard
            v-for="item in similarProducts"
            :key="item.id"
            :product="item"
            @select="emit('open-product', item)"
            @add="emit('add', item)"
          />
        </div>
      </section>
    </section>
    <CartFloating
      :cart="cart"
      :cart-total="cartTotal"
      :cart-count="cartCount"
    :discount-code="discountCode"
    :checkout-error="checkoutError"
      :loading="loading"
      @remove="removeCart"
      @checkout="emit('checkout')"
      @update:discount-code="emit('update:discountCode', $event)"
    />
    <PurchaseHistoryFloating :purchases="purchases" />
  </main>
</template>

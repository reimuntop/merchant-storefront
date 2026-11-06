<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  ChevronDown,
  KeyRound,
  LogOut,
  Mail,
  MapPin,
  MessagesSquare,
  RefreshCcw,
  Search,
  ShieldCheck,
  ShoppingBag,
  Store,
  Trash2,
  Truck,
  UserRound,
  X,
} from "lucide-vue-next";
import AuthPanel from "./components/AuthPanel.vue";
import CreateStoreModal from "./components/CreateStoreModal.vue";
import CartFloating from "./components/CartFloating.vue";
import PurchaseHistoryFloating from "./components/PurchaseHistoryFloating.vue";
import ProductCard from "./components/ProductCard.vue";
import ProductDetail from "./components/ProductDetail.vue";
import StorePage from "./components/StorePage.vue";
import StoreDashboard from "./components/StoreDashboard.vue";
import SavedAddressesModal from "./components/SavedAddressesModal.vue";
import { assetUrl, clearStoredUser, getStoredUser, request, storeUser } from "./api";
import { formatIDR } from "./formatters";

const logoUrl = "/toktok-mark.svg";

const currentUser = ref(getStoredUser());
const products = ref([]);
const cart = ref([]);
const purchases = ref([]);
const selectedProduct = ref(null);
const selectedStoreData = ref(null);
const loading = ref(false);
const notice = ref("");
const checkoutError = ref("");
const discountCode = ref("");
const searchQuery = ref("");
const activeCategory = ref("All");
const accountMenuOpen = ref(false);
const addressesOpen = ref(false);
const profileOpen = ref(false);
const profileBusy = ref(false);
const profileError = ref("");
const profileNotice = ref("");
const profileForm = ref({ displayName: "" });
const changeEmailOpen = ref(false);
const emailBusy = ref(false);
const emailError = ref("");
const emailNotice = ref("");
const emailForm = ref({ email: "" });
const changePasswordOpen = ref(false);
const passwordBusy = ref(false);
const passwordError = ref("");
const passwordNotice = ref("");
const passwordForm = ref({
  currentPassword: "",
  newPassword: "",
});
const deleteAccountOpen = ref(false);
const deleteAccountBusy = ref(false);
const deleteAccountError = ref("");

const myStore = ref(null);
const view = ref("shop");
const createStoreOpen = ref(false);

const cartTotal = computed(() =>
  cart.value.reduce((sum, item) => sum + item.line_total, 0),
);
const cartCount = computed(() =>
  cart.value.reduce((sum, item) => sum + item.quantity, 0),
);
const purchasedProductIds = computed(
  () => new Set(purchases.value.map((purchase) => purchase.product.id)),
);
const categories = computed(() => [
  "All",
  ...new Set(products.value.map((product) => product.category)),
]);
const displayedProducts = computed(() => {
  return products.value.filter(
    (product) =>
      activeCategory.value === "All" ||
      product.category === activeCategory.value,
  );
});

let productSearchTimer;
let productSearchRequest = 0;

watch(searchQuery, (value) => {
  window.clearTimeout(productSearchTimer);
  activeCategory.value = "All";
  const requestId = ++productSearchRequest;
  productSearchTimer = window.setTimeout(async () => {
    if (!currentUser.value) return;
    const query = value.trim();
    const path = query
      ? `/api/products?search=${encodeURIComponent(query)}`
      : "/api/products";
    const rows = await request(path);
    if (requestId === productSearchRequest) products.value = rows;
  }, 250);
});

async function loadAll() {
  if (!currentUser.value) return;
  loading.value = true;
  try {
    const [productRows, cartRows, purchaseRows] = await Promise.all([
      request("/api/products"),
      request(`/api/cart?user_id=${currentUser.value.id}`),
      request(`/api/purchases?user_id=${currentUser.value.id}`),
    ]);
    products.value = productRows;
    cart.value = cartRows;
    purchases.value = purchaseRows;
    selectedProduct.value = selectedProduct.value || productRows[0] || null;
    syncProductRoute();
  } finally {
    loading.value = false;
  }
  await loadMyStore();
}

async function loadMyStore() {
  try {
    myStore.value = await request("/api/stores/me");
  } catch {
    myStore.value = null;
  }
}

async function handleStoreCreated(result) {
  currentUser.value = { ...currentUser.value, access_token: result.access_token };
  storeUser(currentUser.value);
  myStore.value = result.store;
  createStoreOpen.value = false;
  view.value = "store-dashboard";

  try {
    const freshStore = await request("/api/stores/me");
    myStore.value = freshStore;
  } catch (err) {
    console.warn("Store created but refresh failed:", err);
    // Jangan set myStore kembali null.
    // Memastikan object hasil create store sebagai fallback.
  }
}

function openCreateStore() {
  accountMenuOpen.value = false;
  createStoreOpen.value = true;
}

function closeCreateStore() {
  createStoreOpen.value = false;
}

function openStoreDashboard() {
  accountMenuOpen.value = false;
  view.value = "store-dashboard";
}

function backToShop() {
  view.value = "shop";
  window.history.pushState({}, "", "/");
}

async function syncStoreRoute() {
  const match = window.location.pathname.match(/^\/stores\/([^/]+)\/?$/);
  if (!match) return;
  try {
    selectedStoreData.value = await request(`/api/stores/${match[1]}`);
    view.value = "store-detail";
  } catch {
    view.value = "shop";
  }
}

function handlePopState() {
  syncProductRoute();
  syncStoreRoute();
}

function openProductDetail(product) {
  selectedProduct.value = product;
  view.value = "product-detail";
  window.history.pushState(
    { productId: product.id },
    "",
    `/products/${product.id}`,
  );
}

async function openStoreDetail(slug) {
  const storeData = await request(`/api/stores/${slug}`);
  selectedStoreData.value = storeData;
  view.value = "store-detail";
  window.history.pushState({ storeSlug: slug }, "", `/stores/${slug}`);
}

function syncProductRoute() {
  const match = window.location.pathname.match(/^\/products\/(\d+)\/?$/);
  if (!match) {
    if (view.value === "product-detail") view.value = "shop";
    return;
  }
  const product = products.value.find((item) => item.id === Number(match[1]));
  if (product) {
    selectedProduct.value = product;
    view.value = "product-detail";
  }
}

async function addToCart(product, variantId = null) {
  if (product.variants?.length && !variantId) {
    openProductDetail(product);
    return;
  }
  const query = new URLSearchParams({ user_id: String(currentUser.value.id) });
  if (variantId) query.set("variant_id", String(variantId));
  await request(`/api/cart/${product.id}?${query.toString()}`, {
    method: "POST",
  });
  notice.value = `${product.name} added to cart.`;
  await loadAll();
}

async function removeFromCart(productId, variantId = null) {
  const query = new URLSearchParams({ user_id: String(currentUser.value.id) });
  if (variantId) query.set("variant_id", String(variantId));
  await request(`/api/cart/${productId}?${query.toString()}`, {
    method: "DELETE",
  });
  await loadAll();
}

async function checkout() {
  checkoutError.value = "";
  const code = discountCode.value.trim();
  const query = new URLSearchParams({ user_id: String(currentUser.value.id) });
  try {
    if (code) {
      await request("/api/cart/coupon", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
    }
    const result = await request(`/api/checkout?${query.toString()}`, {
      method: "POST",
    });
    notice.value =
      result.status === "empty_cart"
        ? "Cart is empty."
        : result.discount_amount
          ? `Checkout complete. Discount: ${formatIDR(result.discount_amount)}.`
          : "Checkout complete.";
    discountCode.value = "";
    await loadAll();
  } catch (err) {
    checkoutError.value = err.message || "Checkout failed. Please try again.";
  }
}

function handleAuthenticated(user) {
  currentUser.value = user;
  loadAll();
}

function logout() {
  clearStoredUser();
  currentUser.value = null;
  products.value = [];
  cart.value = [];
  purchases.value = [];
  selectedProduct.value = null;
  accountMenuOpen.value = false;
  addressesOpen.value = false;
  deleteAccountOpen.value = false;
  myStore.value = null;
  view.value = "shop";
}

function openDeleteAccount() {
  accountMenuOpen.value = false;
  deleteAccountError.value = "";
  deleteAccountOpen.value = true;
}

function closeDeleteAccount() {
  if (deleteAccountBusy.value) return;
  deleteAccountOpen.value = false;
  deleteAccountError.value = "";
}

async function deleteAccount() {
  deleteAccountBusy.value = true;
  deleteAccountError.value = "";
  try {
    await request("/api/me/account", { method: "DELETE" });
    logout();
  } catch (err) {
    deleteAccountError.value = err.message;
  } finally {
    deleteAccountBusy.value = false;
  }
}

function openChangePassword() {
  accountMenuOpen.value = false;
  changePasswordOpen.value = true;
  passwordError.value = "";
  passwordNotice.value = "";
  passwordForm.value = { currentPassword: "", newPassword: "" };
}

function openChangeEmail() {
  accountMenuOpen.value = false;
  changeEmailOpen.value = true;
  emailError.value = "";
  emailNotice.value = "";
  emailForm.value = { email: currentUser.value.email || "" };
}

function closeChangeEmail() {
  changeEmailOpen.value = false;
  emailError.value = "";
  emailForm.value = { email: "" };
}

async function changeEmail() {
  emailBusy.value = true;
  emailError.value = "";
  emailNotice.value = "";
  try {
    const result = await request("/api/me/email", {
      method: "PATCH",
      body: JSON.stringify({ email: emailForm.value.email }),
    });
    currentUser.value = { ...currentUser.value, email: result.email };
    storeUser(currentUser.value);
    emailForm.value = { email: result.email };
    emailNotice.value = "Email updated.";
  } catch (err) {
    emailError.value = err.message;
  } finally {
    emailBusy.value = false;
  }
}

function openProfile() {
  accountMenuOpen.value = false;
  profileOpen.value = true;
  profileError.value = "";
  profileNotice.value = "";
  profileForm.value = { displayName: currentUser.value.display_name || "" };
}

function openAddresses() {
  accountMenuOpen.value = false;
  addressesOpen.value = true;
}

function closeProfile() {
  profileOpen.value = false;
  profileError.value = "";
  profileForm.value = { displayName: "" };
}

async function updateProfile() {
  profileBusy.value = true;
  profileError.value = "";
  profileNotice.value = "";
  try {
    const updatedUser = await request("/api/me/profile", {
      method: "PATCH",
      body: JSON.stringify({ display_name: profileForm.value.displayName }),
    });
    currentUser.value = { ...currentUser.value, ...updatedUser };
    storeUser(currentUser.value);
    profileNotice.value = "Profile updated.";
  } catch (err) {
    profileError.value = err.message;
  } finally {
    profileBusy.value = false;
  }
}

function closeChangePassword() {
  changePasswordOpen.value = false;
  passwordError.value = "";
  passwordForm.value = { currentPassword: "", newPassword: "" };
}

async function changePassword() {
  passwordError.value = "";
  passwordNotice.value = "";
  passwordBusy.value = true;
  try {
    await request("/api/me/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: passwordForm.value.currentPassword,
        new_password: passwordForm.value.newPassword,
      }),
    });
    passwordNotice.value = "Password changed.";
    passwordForm.value = { currentPassword: "", newPassword: "" };
  } catch (err) {
    passwordError.value = err.message;
  } finally {
    passwordBusy.value = false;
  }
}

onMounted(async () => {
  window.addEventListener("auth:unauthorized", logout);
  window.addEventListener("popstate", handlePopState);
  await loadAll();
  await syncStoreRoute();
});

onBeforeUnmount(() => {
  window.clearTimeout(productSearchTimer);
  window.removeEventListener("auth:unauthorized", logout);
  window.removeEventListener("popstate", handlePopState);
});
</script>

<template>
  <AuthPanel
    v-if="!currentUser"
    @authenticated="handleAuthenticated"
  />

  <StoreDashboard
    v-else-if="view === 'store-dashboard' && myStore"
    :store="myStore"
    @back="backToShop"
    @logout="logout"
    @changed="handleStoreChanged"
  />

  <ProductDetail
    v-else-if="view === 'product-detail' && selectedProduct"
    :product="selectedProduct"
    :user-id="currentUser.id"
    :user="currentUser"
    :my-store="myStore"
    :cart-total="cartTotal"
    :cart-count="cartCount"
    :cart="cart"
    :discount-code="discountCode"
    :checkout-error="checkoutError"
    :purchases="purchases"
    :loading="loading"
    :can-review="purchasedProductIds.has(selectedProduct.id)"
    :products="products"
    @back="backToShop"
    @add="addToCart"
    @open-product="openProductDetail"
    @open-store="openStoreDetail"
    @changed="loadAll"
    @dashboard="openStoreDashboard"
    @create-store="openCreateStore"
    @change-password="openChangePassword"
    @logout="logout"
    @remove-cart="removeFromCart"
    @checkout="checkout"
    @update:discount-code="discountCode = $event"
  />

  <StorePage
    v-else-if="view === 'store-detail' && selectedStoreData"
    :store-data="selectedStoreData"
    :user="currentUser"
    :my-store="myStore"
    :cart="cart"
    :cart-total="cartTotal"
    :cart-count="cartCount"
    :discount-code="discountCode"
    :checkout-error="checkoutError"
    :purchases="purchases"
    :loading="loading"
    @back="backToShop"
    @open-product="openProductDetail"
    @add="addToCart"
    @changed="loadAll"
    @dashboard="openStoreDashboard"
    @create-store="openCreateStore"
    @change-password="openChangePassword"
    @logout="logout"
    @remove-cart="removeFromCart"
    @checkout="checkout"
    @update:discount-code="discountCode = $event"
  />

  <main v-else class="app-shell min-h-screen">
    <header class="site-header sticky top-0 z-30">
      <div class="mx-auto max-w-7xl px-5">
        <div
          class="grid gap-4 py-4 lg:grid-cols-[auto_minmax(260px,1fr)_auto] lg:items-center"
        >
          <div class="flex items-center gap-3">
            <img :src="logoUrl" alt="Belanjoo" class="brand-logo" />
            <div class="min-w-0">
              <p class="text-lg font-semibold leading-6 text-ink">
                Belanjoo
              </p>
              <p class="truncate text-xs font-medium text-[#68635d]">
                Curated goods for work and home
              </p>
            </div>
          </div>

          <label class="relative block">
            <Search
              class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#68635d]"
            />
            <input
              v-model="searchQuery"
              class="h-11 w-full border border-line bg-white pl-10 pr-4 text-sm outline-none transition focus:border-moss"
              style="border-radius: 8px"
              placeholder="Search products, categories, or details"
              type="search"
            />
          </label>

          <div class="flex items-center justify-between gap-2 lg:justify-end">
            <button
              class="secondary-button h-11 px-3"
              :disabled="loading"
              title="Refresh data"
              @click="loadAll"
            >
              <RefreshCcw class="h-4 w-4" />
              <span class="hidden sm:inline">Refresh</span>
            </button>
            <div class="relative">
              <button
                class="secondary-button h-11 px-3"
                title="Account"
                @click="accountMenuOpen = !accountMenuOpen"
              >
                <UserRound class="h-4 w-4" />
                <span class="max-w-[120px] truncate">{{
                  currentUser.display_name
                }}</span>
                <ChevronDown class="h-4 w-4 text-[#68635d]" />
              </button>
              <div
                v-if="accountMenuOpen"
                class="absolute right-0 top-12 z-40 w-56 border border-line bg-white p-2 shadow-panel"
                style="border-radius: 8px"
              >
                <div class="border-b border-line px-3 py-2">
                  <p class="truncate text-sm font-semibold">
                    {{ currentUser.display_name }}
                  </p>
                  <p class="truncate text-xs text-[#68635d]">
                    {{ currentUser.username }}
                  </p>
                </div>
                <button
                  v-if="myStore"
                  class="mt-2 flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-ink hover:bg-field"
                  style="border-radius: 8px"
                  @click="openStoreDashboard"
                >
                  <Store class="h-4 w-4 text-moss" />
                  Store Dashboard
                </button>
                <button
                  v-else
                  class="mt-2 flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-ink hover:bg-field"
                  style="border-radius: 8px"
                  @click="openCreateStore"
                >
                  <Store class="h-4 w-4 text-moss" />
                  Create Store
                </button>
                <button
                  class="mt-1 flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-ink hover:bg-field"
                  style="border-radius: 8px"
                  @click="openAddresses"
                >
                  <MapPin class="h-4 w-4 text-moss" />
                  Saved Addresses
                </button>
                <button
                  class="mt-1 flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-ink hover:bg-field"
                  style="border-radius: 8px"
                  @click="openProfile"
                >
                  <UserRound class="h-4 w-4 text-moss" />
                  Edit Profile
                </button>
                <button
                  class="mt-1 flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-ink hover:bg-field"
                  style="border-radius: 8px"
                  @click="openChangePassword"
                >
                  <KeyRound class="h-4 w-4 text-moss" />
                  Change Password
                </button>
                <button
                  class="mt-1 flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-ink hover:bg-field"
                  style="border-radius: 8px"
                  @click="openChangeEmail"
                >
                  <Mail class="h-4 w-4 text-moss" />
                  Change Email
                </button>
                <button
                  class="mt-1 flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-ember hover:bg-[#f8eae5]"
                  style="border-radius: 8px"
                  @click="openDeleteAccount"
                >
                  <Trash2 class="h-4 w-4" />
                  Delete Account
                </button>
                <button
                  class="mt-1 flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-ember hover:bg-[#f8eae5]"
                  style="border-radius: 8px"
                  @click="logout"
                >
                  <LogOut class="h-4 w-4" />
                  Logout
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="border-t border-line/70">
          <div class="flex items-center gap-2 overflow-x-auto py-2.5">
            <ShoppingBag class="h-4 w-4 shrink-0 text-[#1e3d2b]" />
            <button
              v-for="category in categories"
              :key="category"
              class="shrink-0 px-3 py-1.5 text-sm font-semibold transition r-ctl"
              :class="
                activeCategory === category
                  ? 'bg-[#1e3d2b] text-white'
                  : 'text-[#5e5953] hover:bg-[#f4efe6]'
              "
              @click="activeCategory = category"
            >
              {{ category }}
            </button>
          </div>
        </div>
      </div>
    </header>

    <section class="mx-auto max-w-7xl px-5 py-6">
      <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_312px] lg:items-start">
        <div class="min-w-0 space-y-5">
          <div class="flex items-end justify-between gap-4">
            <div>
              <h1 class="text-xl font-bold tracking-tight">Produk terbaru</h1>
              <p class="text-sm text-[#68635d]">
                {{ displayedProducts.length }} produk siap kirim
              </p>
            </div>
            <p
              v-if="notice"
              class="max-w-sm text-right text-sm font-medium text-[#1e3d2b] md:hidden"
            >
              {{ notice }}
            </p>
          </div>

          <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 xl:grid-cols-4">
            <ProductCard
              v-for="product in displayedProducts"
              :key="product.id"
              class="h-full"
              :product="product"
              :selected="selectedProduct?.id === product.id"
              @select="openProductDetail(product)"
              @add="addToCart(product)"
            />
          </div>

          <div
            v-if="!displayedProducts.length"
            class="border border-dashed border-line bg-white p-10 text-center text-sm text-[#68635d] r-panel"
          >
            Belum ada produk untuk kategori ini. Coba pilih kategori lain atau ubah kata kunci
            pencarianmu.
          </div>
        </div>

        <aside class="space-y-4">
          <div class="border border-line bg-[#1e3d2b] p-5 text-white r-panel">
            <p class="text-xs font-medium text-white/70">Tokonya orang lokal</p>
            <h2 class="mt-1.5 text-lg font-bold leading-6">Jual barangmu di Belanjoo.</h2>
            <p class="mt-2 text-sm leading-6 text-white/75">
              Buka toko, atur produk, dan kelola pesanan dari dashboard penjual.
            </p>
            <button
              v-if="!myStore"
              class="mt-4 w-full bg-white px-3 py-2.5 text-sm font-semibold text-[#1e3d2b] transition hover:bg-[#f4efe6] r-ctl"
              @click="openCreateStore"
            >
              Buka toko gratis
            </button>
            <button
              v-else
              class="mt-4 w-full bg-white px-3 py-2.5 text-sm font-semibold text-[#1e3d2b] transition hover:bg-[#f4efe6] r-ctl"
              @click="openStoreDashboard"
            >
              Buka dashboard toko
            </button>
          </div>

          <div class="border border-line bg-white p-4 r-panel">
            <h2 class="text-sm font-bold">Kategori</h2>
            <div class="mt-3 flex flex-wrap gap-2">
              <button
                v-for="category in categories"
                :key="`rail-${category}`"
                class="border border-line px-3 py-1.5 text-xs font-semibold transition r-ctl"
                :class="
                  activeCategory === category
                    ? 'border-[#1e3d2b] bg-[#1e3d2b] text-white'
                    : 'text-[#5e5953] hover:border-[#1e3d2b] hover:text-[#1e3d2b]'
                "
                @click="activeCategory = category"
              >
                {{ category }}
              </button>
            </div>
          </div>

          <div class="border border-line bg-white p-4 r-panel">
            <h2 class="text-sm font-bold">Kenapa Belanjoo</h2>
            <ul class="mt-3 space-y-2 text-sm text-[#5e5953]">
              <li class="flex gap-2"><ShieldCheck class="h-4 w-4 shrink-0 text-[#1e3d2b]" />Penjual terverifikasi</li>
              <li class="flex gap-2"><Truck class="h-4 w-4 shrink-0 text-[#1e3d2b]" />Kirim ke seluruh Indonesia</li>
              <li class="flex gap-2"><MessagesSquare class="h-4 w-4 shrink-0 text-[#1e3d2b]" />Tanya jawab langsung dengan penjual</li>
            </ul>
          </div>
        </aside>
      </div>
    </section>

    <footer class="mt-12 bg-[#1e3d2b] text-white/80">
      <div class="mx-auto grid max-w-7xl gap-8 px-5 py-10 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <div class="flex items-center gap-2.5">
            <img :src="logoUrl" alt="Belanjoo" class="h-9 w-9" />
            <p class="text-base font-bold text-white">Belanjoo</p>
          </div>
          <p class="mt-3 text-sm leading-6">
            Barang sehari-hari dari penjual lokal, dikirim ke seluruh Indonesia.
          </p>
        </div>
        <div>
          <p class="text-sm font-bold text-white">Jelajahi</p>
          <ul class="mt-3 space-y-2 text-sm">
            <li>Semua produk</li>
            <li>Kategori</li>
            <li>Produk terbaru</li>
            <li>Ulasan pembeli</li>
          </ul>
        </div>
        <div>
          <p class="text-sm font-bold text-white">Jualan</p>
          <ul class="mt-3 space-y-2 text-sm">
            <li>Buka toko</li>
            <li>Dashboard penjual</li>
            <li>Panduan pengiriman</li>
            <li>Pusat bantuan</li>
          </ul>
        </div>
        <div>
          <p class="text-sm font-bold text-white">Ikuti kami</p>
          <div class="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm">
            <a href="https://www.facebook.com/belanjoo_ecommerce" target="_blank" rel="noopener noreferrer" class="transition hover:text-white">Facebook</a>
            <a href="https://tiktok.com/belanjoo_ecommerce" target="_blank" rel="noopener noreferrer" class="transition hover:text-white">Tiktok</a>
            <a href="https://www.instagram.com/belanjoo_ecommerce" target="_blank" rel="noopener noreferrer" class="transition hover:text-white">Instagram</a>
            <a href="https://www.linkedin.com/belanjoo_ecommerce" target="_blank" rel="noopener noreferrer" class="transition hover:text-white">LinkedIn</a>
          </div>
        </div>
      </div>
      <div class="border-t border-white/15">
        <div class="mx-auto flex max-w-7xl flex-col gap-2 px-5 py-4 text-xs sm:flex-row sm:items-center sm:justify-between">
          <p>&copy; 2026 Belanjoo. Lingkungan lab lokal.</p>
          <p>Harga sudah termasuk PPN.</p>
        </div>
      </div>
    </footer>

    <CartFloating
      :cart="cart"
      :cart-total="cartTotal"
      :cart-count="cartCount"
      :discount-code="discountCode"
      :checkout-error="checkoutError"
      :loading="loading"
      @remove="removeFromCart"
      @checkout="checkout"
      @update:discount-code="discountCode = $event"
    />
    <PurchaseHistoryFloating :purchases="purchases" />
    <SavedAddressesModal :open="addressesOpen" @close="addressesOpen = false" />

    <div
      v-if="profileOpen"
      class="fixed inset-0 z-50 grid place-items-center bg-black/45 p-5"
    >
      <form
        class="w-full max-w-md border border-line bg-white p-5 shadow-panel"
        style="border-radius: 8px"
        @submit.prevent="updateProfile"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold">Edit Profile</h2>
            <p class="mt-1 text-sm text-[#68635d]">Update your display name.</p>
          </div>
          <button type="button" class="icon-button h-9 w-9" title="Close" @click="closeProfile">
            <X class="h-4 w-4" />
          </button>
        </div>

        <label class="mt-5 block text-sm font-medium text-[#4d4944]" for="profile-display-name">Display Name</label>
        <input
          id="profile-display-name"
          v-model="profileForm.displayName"
          class="mt-2 w-full border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss"
          style="border-radius: 8px"
          autocomplete="name"
        />

        <p v-if="profileError" class="mt-4 border border-ember bg-[#f8eae5] px-3 py-2 text-sm text-ember" style="border-radius: 8px">{{ profileError }}</p>
        <p v-if="profileNotice" class="mt-4 border border-moss bg-[#f4efe6] px-3 py-2 text-sm font-medium text-[#b3261e]" style="border-radius: 8px">{{ profileNotice }}</p>

        <div class="mt-5 flex justify-end gap-3">
          <button type="button" class="secondary-button" @click="closeProfile">Cancel</button>
          <button class="primary-button" :disabled="profileBusy">Save Profile</button>
        </div>
      </form>
    </div>

    <div
      v-if="changeEmailOpen"
      class="fixed inset-0 z-50 grid place-items-center bg-black/45 p-5"
    >
      <form
        class="w-full max-w-md border border-line bg-white p-5 shadow-panel"
        style="border-radius: 8px"
        @submit.prevent="changeEmail"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold">Change Email</h2>
            <p class="mt-1 text-sm text-[#68635d]">
              Update the email address for your account.
            </p>
          </div>
          <button
            type="button"
            class="icon-button h-9 w-9"
            title="Close"
            :disabled="emailBusy"
            @click="closeChangeEmail"
          >
            <X class="h-4 w-4" />
          </button>
        </div>

        <div class="mt-5 border border-line bg-field px-3 py-2" style="border-radius: 8px">
          <p class="text-xs font-semibold uppercase tracking-wide text-[#68635d]">Current Email</p>
          <p class="mt-1 text-sm font-medium text-ink">{{ currentUser.email || "Not set" }}</p>
        </div>

        <label class="mt-4 block text-sm font-medium text-[#4d4944]" for="new-email">New Email</label>
        <input
          id="new-email"
          v-model="emailForm.email"
          class="mt-2 w-full border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss"
          style="border-radius: 8px"
          type="email"
          autocomplete="email"
          required
        />

        <p v-if="emailError" class="mt-4 border border-ember bg-[#f8eae5] px-3 py-2 text-sm text-ember" style="border-radius: 8px">{{ emailError }}</p>
        <p v-if="emailNotice" class="mt-4 border border-moss bg-[#f4efe6] px-3 py-2 text-sm font-medium text-[#b3261e]" style="border-radius: 8px">{{ emailNotice }}</p>

        <div class="mt-5 flex justify-end gap-3">
          <button type="button" class="secondary-button" :disabled="emailBusy" @click="closeChangeEmail">Cancel</button>
          <button class="primary-button" :disabled="emailBusy">
            <Mail class="h-4 w-4" />
            {{ emailBusy ? "Updating..." : "Update Email" }}
          </button>
        </div>
      </form>
    </div>

    <div
      v-if="changePasswordOpen"
      class="fixed inset-0 z-50 grid place-items-center bg-black/45 p-5"
    >
      <form
        class="w-full max-w-md border border-line bg-white p-5 shadow-panel"
        style="border-radius: 8px"
        @submit.prevent="changePassword"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold">Change Password</h2>
            <p class="mt-1 text-sm text-[#68635d]">
              Update the password for {{ currentUser.display_name }}.
            </p>
          </div>
          <button
            type="button"
            class="icon-button h-9 w-9"
            title="Close"
            @click="closeChangePassword"
          >
            <X class="h-4 w-4" />
          </button>
        </div>

        <label
          class="mt-5 block text-sm font-medium text-[#4d4944]"
          for="current-password"
          >Current Password</label
        >
        <input
          id="current-password"
          v-model="passwordForm.currentPassword"
          class="mt-2 w-full border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss"
          style="border-radius: 8px"
          type="password"
          autocomplete="current-password"
          required
        />

        <label
          class="mt-4 block text-sm font-medium text-[#4d4944]"
          for="new-password"
          >New Password</label
        >
        <input
          id="new-password"
          v-model="passwordForm.newPassword"
          class="mt-2 w-full border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss"
          style="border-radius: 8px"
          type="password"
          autocomplete="new-password"
          required
        />

        <p
          v-if="passwordError"
          class="mt-4 border border-ember bg-[#f8eae5] px-3 py-2 text-sm text-ember"
          style="border-radius: 8px"
        >
          {{ passwordError }}
        </p>
        <p
          v-if="passwordNotice"
          class="mt-4 border border-moss bg-[#f4efe6] px-3 py-2 text-sm font-medium text-[#b3261e]"
          style="border-radius: 8px"
        >
          {{ passwordNotice }}
        </p>

        <div class="mt-5 flex justify-end gap-3">
          <button
            type="button"
            class="secondary-button"
            @click="closeChangePassword"
          >
            Cancel
          </button>
          <button class="primary-button" :disabled="passwordBusy">
            <KeyRound class="h-4 w-4" />
            Change Password
          </button>
        </div>
      </form>
    </div>

    <div
      v-if="deleteAccountOpen"
      class="fixed inset-0 z-50 grid place-items-center bg-black/45 p-5"
    >
      <form
        class="w-full max-w-md border border-line bg-white p-5 shadow-panel"
        style="border-radius: 8px"
        @submit.prevent="deleteAccount"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold">Delete Account</h2>
            <p class="mt-1 text-sm text-[#68635d]">
              This permanently removes your account. You will be signed out.
            </p>
          </div>
          <button
            type="button"
            class="icon-button h-9 w-9"
            title="Close"
            :disabled="deleteAccountBusy"
            @click="closeDeleteAccount"
          >
            <X class="h-4 w-4" />
          </button>
        </div>

        <p
          v-if="deleteAccountError"
          class="mt-4 border border-ember bg-[#f8eae5] px-3 py-2 text-sm text-ember"
          style="border-radius: 8px"
        >
          {{ deleteAccountError }}
        </p>

        <div class="mt-5 flex justify-end gap-3">
          <button
            type="button"
            class="secondary-button"
            :disabled="deleteAccountBusy"
            @click="closeDeleteAccount"
          >
            Cancel
          </button>
          <button
            class="primary-button bg-ember hover:bg-[#b92a20]"
            :disabled="deleteAccountBusy"
          >
            <Trash2 class="h-4 w-4" />
            {{ deleteAccountBusy ? "Deleting..." : "Delete Account" }}
          </button>
        </div>
      </form>
    </div>
  </main>

  <CreateStoreModal
    v-if="createStoreOpen"
    @close="closeCreateStore"
    @created="handleStoreCreated"
  />

</template>

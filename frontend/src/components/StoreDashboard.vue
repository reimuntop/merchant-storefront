<script setup>
import { computed, onMounted, ref } from "vue";
import {
  ArrowLeft,
  BadgePercent,
  ClipboardList,
  FolderOpen,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Package,
  Plus,
  Settings,
  ShoppingBag,
  Star,
  Store,
  Tags,
  Trash2,
  Upload,
  Users,
  UserRoundCog,
  Webhook,
  X,
} from "lucide-vue-next";
import { API_BASE, assetUrl, getStoredUser, request } from "../api";
import { formatIDR } from "../formatters";

const props = defineProps({ store: { type: Object, required: true } });
const emit = defineEmits(["back", "logout", "changed"]);

const sections = [
  { key: "overview", label: "Overview", icon: LayoutDashboard },
  { key: "products", label: "My Products", icon: Package },
  { key: "categories", label: "Categories", icon: Tags },
  { key: "discounts", label: "Discounts", icon: BadgePercent },
  { key: "analytics", label: "Penjualan", icon: LayoutDashboard },
  { key: "customers", label: "Customers", icon: Users },
  { key: "orders", label: "Incoming Orders", icon: ShoppingBag },
  { key: "reviews", label: "Store Reviews", icon: Star },
  { key: "questions", label: "Product Q&A", icon: MessageSquare },
  { key: "settings", label: "Store Settings", icon: Settings },
  { key: "webhook", label: "Webhook Settings", icon: Webhook },
  { key: "media", label: "Media Manager", icon: FolderOpen },
  { key: "team", label: "Team", icon: UserRoundCog },
];

const activeSection = ref("overview");
const categories = ref([]);
const products = ref([]);
const orders = ref([]);
const internalNoteDrafts = ref({});
const packingSlips = ref({});
const discounts = ref([]);
const analytics = ref({ total_sales: 0, order_count: 0, top_products: [] });
const customers = ref([]);
const storeReviews = ref({ items: [], review_count: 0, average_rating: 0 });
const storeQuestions = ref([]);
const answerDrafts = ref({});
const questionFilter = ref("unanswered");
const visibleQuestions = computed(() => storeQuestions.value.filter(question =>
  questionFilter.value === "answered" ? Boolean(question.answered_at) : !question.answered_at
));

// Resolve a product's image by id so analytics rows (which carry no image of
// their own) can borrow the thumbnail already loaded for the catalog.
const productById = computed(() =>
  new Map(products.value.map((product) => [product.id, product])),
);
const topProducts = computed(() =>
  analytics.value.top_products.map((item) => ({
    ...item,
    image_url: productById.value.get(item.product_id)?.image_url || "",
  })),
);

async function answerQuestion(question) {
  const answer = answerDrafts.value[question.id] || "";
  if (!answer.trim() || busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    const updated = await request(`/api/stores/me/questions/${question.id}/answer`, {
      method: "PATCH", body: JSON.stringify({ answer }),
    });
    storeQuestions.value = storeQuestions.value.map(row => row.id === updated.id ? updated : row);
    delete answerDrafts.value[question.id];
    notice.value = "Answer saved.";
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}
const teamMembers = ref([]);
const media = ref([]);
const mediaPath = ref("");
const mediaPreview = ref(null);
const webhook = ref(null);
const webhookForm = ref({ name: "Discord notifications", url: "", active: true });
const webhookTestUrl = ref("");
const webhookTestResult = ref(null);
const emailPreviewForm = ref({
  subject: "Order Update",
  body: "Halo {{ customer_name }},\nPesanan {{ order_id }} sedang diproses oleh {{ store_name }}.",
});
const emailPreviewResult = ref(null);
const teamForm = ref({ username: "", display_name: "", password: "", role: "viewer" });
const profileForm = ref({
  name: "",
  description: "",
  category: "",
  city: "",
  phone: "",
  address: "",
  opening_hours: "",
  return_policy: "",
});
const storeFileNames = ref({ logo: "", banner: "" });
const selectedVariantProduct = ref(null);
const variants = ref([]);
const variantForm = ref({
  name: "",
  size: "",
  color: "",
  sku: "",
  stock: 0,
  price: "",
});
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const notice = ref("");
const categoryName = ref("");
const editingCategoryId = ref(null);
const discountForm = ref({
  code: "",
  kind: "percentage",
  value: 10,
  min_subtotal: 0,
  usage_limit: "",
  scope: "all",
  target_id: "",
});
const editingDiscountId = ref(null);
const editingProductId = ref(null);
const imageImportUrl = ref("");
const imageImportBusy = ref(false);
const imageImportError = ref("");
const productForm = ref({
  name: "",
  description: "",
  price: 0,
  image_url: "",
  category_id: "",
  stock: 0,
  sku: "",
  status: "draft",
});
const canEdit = computed(() => props.store.access_role === "owner" || props.store.access_role === "editor");
const isOwner = computed(() => props.store.access_role === "owner");

function resetProduct() {
  editingProductId.value = null;
  imageImportUrl.value = "";
  imageImportError.value = "";
  productForm.value = {
    name: "",
    description: "",
    price: 0,
    image_url: "",
    category_id: "",
    stock: 0,
    sku: "",
    status: "draft",
  };
}

async function loadCatalog() {
  loading.value = true;
  error.value = "";
  try {
    [
      categories.value,
      products.value,
      orders.value,
      discounts.value,
      analytics.value,
      customers.value,
      storeReviews.value,
      storeQuestions.value,
      teamMembers.value,
      webhook.value,
      media.value,
    ] = await Promise.all([
      request("/api/stores/me/categories"),
      request("/api/stores/me/products"),
      request("/api/stores/me/orders"),
      request("/api/stores/me/discounts"),
      request("/api/stores/me/analytics/sales"),
      request("/api/stores/me/customers"),
      request("/api/stores/me/reviews"),
      request("/api/stores/me/questions"),
      request("/api/stores/me/team"),
      request("/api/stores/me/webhook"),
      request("/api/stores/me/media"),
    ]);
    if (canEdit.value) {
      const notes = await Promise.all(
        orders.value.map((order) =>
          request(`/api/orders/${order.id}/internal-notes`),
        ),
      );
      internalNoteDrafts.value = Object.fromEntries(
        notes.map((note) => [note.order_id, note.internal_note || ""]),
      );
    } else {
      internalNoteDrafts.value = {};
    }
    if (webhook.value) {
      webhookForm.value = {
        name: webhook.value.name,
        url: webhook.value.url,
        active: webhook.value.active,
      };
      webhookTestUrl.value = webhook.value.url;
    }
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function reconcileInventory() {
  busy.value = true;
  error.value = "";
  try {
    const result = await request("/api/stores/me/inventory/reconcile", {
      method: "POST",
    });
    notice.value = result.updated
      ? `Inventory reconciled. ${result.updated} product${result.updated === 1 ? "" : "s"} updated.`
      : "Inventory is already consistent.";
    await loadCatalog();
  } catch (err) {
    error.value = err.message || "Inventory reconciliation failed.";
  } finally {
    busy.value = false;
  }
}

async function previewMedia(path = mediaPath.value) {
  if (!path.trim()) return;
  busy.value = true;
  error.value = "";
  try {
    const session = getStoredUser();
    const response = await fetch(`${API_BASE}/api/stores/me/media/preview?path=${encodeURIComponent(path.trim())}`, {
      headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.detail || `Preview failed: ${response.status}`);
    }
    if (mediaPreview.value?.url) URL.revokeObjectURL(mediaPreview.value.url);
    mediaPreview.value = {
      name: path.trim(),
      url: URL.createObjectURL(await response.blob()),
      contentType: response.headers.get("content-type") || "application/octet-stream",
    };
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

async function saveWebhook() {
  busy.value = true;
  error.value = "";
  try {
    webhook.value = await request("/api/stores/me/webhook", {
      method: "POST",
      body: JSON.stringify(webhookForm.value),
    });
    webhookTestUrl.value = webhook.value.url;
    notice.value = "Discord webhook saved successfully.";
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

async function testWebhook() {
  if (!webhookTestUrl.value.trim()) return;
  busy.value = true;
  error.value = "";
  webhookTestResult.value = null;
  try {
    webhookTestResult.value = await request("/api/stores/me/webhook/test", {
      method: "POST",
      body: JSON.stringify({ url: webhookTestUrl.value }),
    });
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

async function deleteWebhook() {
  if (!window.confirm("Delete the configured Discord webhook?")) return;
  try {
    await request("/api/stores/me/webhook", { method: "DELETE" });
    webhook.value = null;
    webhookForm.value = { name: "Discord notifications", url: "", active: true };
    webhookTestUrl.value = "";
    webhookTestResult.value = null;
    notice.value = "Discord webhook deleted successfully.";
  } catch (err) {
    error.value = err.message;
  }
}

async function saveTeamMember() {
  busy.value = true;
  error.value = "";
  try {
    await request("/api/stores/me/team", { method: "POST", body: JSON.stringify(teamForm.value) });
    teamForm.value = { username: "", display_name: "", password: "", role: "viewer" };
    notice.value = "Team account created successfully.";
    teamMembers.value = await request("/api/stores/me/team");
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

async function updateTeamMember(member, changes) {
  try {
    await request(`/api/stores/me/team/${member.id}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    });
    notice.value = "Team member updated successfully.";
    await loadCatalog();
  } catch (err) {
    error.value = err.message;
  }
}

async function resetTeamPassword(member) {
  const password = window.prompt(`Enter a new password for ${member.username} (minimum 8 characters):`);
  if (password === null) return;
  if (password.length < 8) {
    error.value = "Password must be at least 8 characters.";
    return;
  }
  await updateTeamMember(member, { password });
}

async function removeTeamMember(member) {
  if (!window.confirm(`Remove team access for ${member.username}?`)) return;
  try {
    await request(`/api/stores/me/team/${member.id}`, { method: "DELETE" });
    notice.value = "Team member removed successfully.";
    await loadCatalog();
  } catch (err) {
    error.value = err.message;
  }
}

async function saveProfile() {
  busy.value = true;
  error.value = "";
  try {
    await request("/api/stores/me", {
      method: "PATCH",
      body: JSON.stringify(profileForm.value),
    });
    notice.value = "Store profile updated successfully.";
    emit("changed");
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

async function previewEmail() {
  busy.value = true;
  error.value = "";
  emailPreviewResult.value = null;
  try {
    emailPreviewResult.value = await request("/api/stores/me/email-preview", {
      method: "POST",
      body: JSON.stringify(emailPreviewForm.value),
    });
    notice.value = "Email preview rendered.";
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

async function uploadStoreImage(imageType, event) {
  const file = event.target.files?.[0];
  if (!file) return;
  storeFileNames.value[imageType] = file.name;
  const form = new FormData();
  form.append("file", file);
  busy.value = true;
  error.value = "";
  try {
    const result = await request(`/api/stores/me/image/${imageType}`, {
      method: "POST",
      body: form,
    });
    profileForm.value[`${imageType}_url`] = result.image_url;
    notice.value = `${imageType[0].toUpperCase()}${imageType.slice(1)} uploaded successfully.`;
    emit("changed");
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
    event.target.value = "";
  }
}

async function openVariants(product) {
  selectedVariantProduct.value = product;
  variants.value = await request(
    `/api/stores/me/products/${product.id}/variants`,
  );
}

async function saveVariant() {
  if (!selectedVariantProduct.value) return;
  busy.value = true;
  try {
    await request(
      `/api/stores/me/products/${selectedVariantProduct.value.id}/variants`,
      {
        method: "POST",
        body: JSON.stringify({
          ...variantForm.value,
          stock: Number(variantForm.value.stock),
          price:
            variantForm.value.price === ""
              ? null
              : Number(variantForm.value.price),
        }),
      },
    );
    variantForm.value = {
      name: "",
      size: "",
      color: "",
      sku: "",
      stock: 0,
      price: "",
    };
    await openVariants(selectedVariantProduct.value);
    notice.value = "Variant added successfully.";
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

async function uploadProductImage(product, event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  try {
    await request(`/api/stores/me/products/${product.id}/image`, {
      method: "POST",
      body: form,
    });
    notice.value = "Product image uploaded successfully.";
    await loadCatalog();
  } catch (err) {
    error.value = err.message;
  }
}

async function saveDiscount() {
  busy.value = true;
  error.value = "";
  const payload = {
    ...discountForm.value,
    value: Number(discountForm.value.value),
    min_subtotal: Number(discountForm.value.min_subtotal),
    usage_limit: discountForm.value.usage_limit
      ? Number(discountForm.value.usage_limit)
      : null,
    target_id:
      discountForm.value.scope === "all"
        ? null
        : Number(discountForm.value.target_id),
  };
  const isEditing = Boolean(editingDiscountId.value);
  try {
    await request(
      isEditing
        ? `/api/stores/me/discounts/${editingDiscountId.value}`
        : "/api/stores/me/discounts",
      {
      method: isEditing ? "PATCH" : "POST",
      body: JSON.stringify(payload),
      },
    );
    discountForm.value = {
      code: "",
      kind: "percentage",
      value: 10,
      min_subtotal: 0,
      usage_limit: "",
      scope: "all",
      target_id: "",
    };
    editingDiscountId.value = null;
    notice.value = isEditing
      ? "Discount updated successfully."
      : "Discount created successfully.";
    await loadCatalog();
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

function editDiscount(discount) {
  editingDiscountId.value = discount.id;
  discountForm.value = {
    code: discount.code,
    kind: discount.kind,
    value: discount.value,
    min_subtotal: discount.min_subtotal,
    usage_limit: discount.usage_limit || "",
    scope: discount.scope || "all",
    target_id: discount.target_id || "",
  };
}

function cancelDiscountEdit() {
  editingDiscountId.value = null;
  discountForm.value = {
    code: "",
    kind: "percentage",
    value: 10,
    min_subtotal: 0,
    usage_limit: "",
    scope: "all",
    target_id: "",
  };
}

async function removeDiscount(discount) {
  if (!window.confirm(`Delete discount ${discount.code}?`)) return;
  try {
    await request(`/api/stores/me/discounts/${discount.id}`, { method: "DELETE" });
    notice.value = "Discount deleted successfully.";
    await loadCatalog();
  } catch (err) {
    error.value = err.message;
  }
}

async function toggleDiscount(discount) {
  try {
    await request(`/api/stores/me/discounts/${discount.id}`, {
      method: "PATCH",
      body: JSON.stringify({ active: !discount.active }),
    });
    await loadCatalog();
  } catch (err) {
    error.value = err.message;
  }
}

async function updateOrder(order, status) {
  try {
    await request(`/api/stores/me/orders/${order.id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    notice.value = "Order status updated successfully.";
    await loadCatalog();
  } catch (err) {
    error.value = err.message;
  }
}

async function saveInternalNote(order) {
  busy.value = true;
  error.value = "";
  try {
    const result = await request(
      `/api/stores/me/orders/${order.id}/internal-note`,
      {
        method: "PATCH",
        body: JSON.stringify({
          internal_note: internalNoteDrafts.value[order.id] || null,
        }),
      },
    );
    order.internal_note = result.internal_note;
    internalNoteDrafts.value[order.id] = result.internal_note || "";
    notice.value = "Internal note saved.";
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

async function viewPackingSlip(order) {
  if (packingSlips.value[order.id]) {
    const updated = { ...packingSlips.value };
    delete updated[order.id];
    packingSlips.value = updated;
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    const slip = await request(`/api/orders/${order.id}/packing-slip`);
    packingSlips.value = { ...packingSlips.value, [order.id]: slip };
  } catch (err) {
    error.value = err.message || "Packing slip could not be loaded.";
  } finally {
    busy.value = false;
  }
}

// Download invoice as a text file
async function downloadInvoice(orderId) {
  try {
    const session = getStoredUser();
    const response = await fetch(
      `${API_BASE}/api/stores/me/orders/${orderId}/invoice/download`,
      {
        headers: session?.access_token
          ? {
              Authorization: `Bearer ${session.access_token}`,
            }
          : {},
      },
    );

    if (!response.ok) {
      const message = await response.text();
      throw new Error(
        `Failed to download invoice (${response.status}): ${message}`,
      );
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `invoice-${orderId}.txt`;

    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
  } catch (err) {
    console.error("Invoice download failed:", err);
  }
}

async function exportOrders() {
  busy.value = true;
  error.value = "";
  try {
    const tools = await import("../features/orderExport.js");
    await tools.downloadOrderExport();
    notice.value = "Order export downloaded successfully.";
  } catch (err) {
    error.value = err.message || "Order export could not be downloaded.";
  } finally {
    busy.value = false;
  }
}

async function generateStoredExport() {
  busy.value = true;
  error.value = "";
  try {
    const tools = await import("../features/orderExport.js");
    const artifact = await tools.generateAndDownloadOrderExport();
    notice.value = `Export #${artifact.id} generated and downloaded.`;
  } catch (err) {
    error.value = err.message || "Stored export could not be generated.";
  } finally {
    busy.value = false;
  }
}

async function saveCategory() {
  if (!categoryName.value.trim()) return;
  busy.value = true;
  error.value = "";
  try {
    const isEditing = Boolean(editingCategoryId.value);
    await request(
      isEditing
        ? `/api/stores/me/categories/${editingCategoryId.value}`
        : "/api/stores/me/categories",
      {
      method: isEditing ? "PATCH" : "POST",
      body: JSON.stringify({ name: categoryName.value }),
      },
    );
    categoryName.value = "";
    editingCategoryId.value = null;
    notice.value = isEditing
      ? "Category updated successfully."
      : "Category added successfully.";
    await loadCatalog();
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

function editCategory(category) {
  editingCategoryId.value = category.id;
  categoryName.value = category.name;
}

function cancelCategoryEdit() {
  editingCategoryId.value = null;
  categoryName.value = "";
}

async function removeCategory(category) {
  if (!window.confirm(`Delete category ${category.name}?`)) return;
  try {
    await request(`/api/stores/me/categories/${category.id}`, {
      method: "DELETE",
    });
    notice.value = "Category deleted successfully.";
    await loadCatalog();
  } catch (err) {
    error.value = err.message;
  }
}

function editProduct(product) {
  editingProductId.value = product.id;
  imageImportUrl.value = "";
  imageImportError.value = "";
  productForm.value = {
    name: product.name,
    description: product.description,
    price: product.price,
    image_url: product.image_url || "",
    category_id: product.category_id || "",
    stock: product.stock ?? 0,
    sku: product.sku || "",
    status: product.status === "out-of-stock" ? "active" : product.status,
  };
}

async function importProductImage() {
  const url = imageImportUrl.value.trim();
  if (!url) return;
  imageImportBusy.value = true;
  imageImportError.value = "";
  try {
    const result = await request("/api/stores/me/products/import-image", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
    productForm.value.image_url = result.image_url;
    notice.value = "Product image imported successfully.";
  } catch (err) {
    imageImportError.value = err.message;
  } finally {
    imageImportBusy.value = false;
  }
}

async function saveProduct() {
  busy.value = true;
  error.value = "";
  const payload = {
    ...productForm.value,
    price: Number(productForm.value.price),
    stock: Number(productForm.value.stock),
    category_id: productForm.value.category_id
      ? Number(productForm.value.category_id)
      : null,
  };
  try {
    await request(
      editingProductId.value
        ? `/api/stores/me/products/${editingProductId.value}`
        : "/api/stores/me/products",
      {
        method: editingProductId.value ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      },
    );
    notice.value = editingProductId.value
      ? "Product updated successfully."
      : "Product added successfully.";
    resetProduct();
    await loadCatalog();
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

async function removeProduct(product) {
  if (!window.confirm(`Delete product ${product.name}?`)) return;
  try {
    await request(`/api/stores/me/products/${product.id}`, {
      method: "DELETE",
    });
    notice.value = "Product deleted successfully.";
    await loadCatalog();
  } catch (err) {
    error.value = err.message;
  }
}

onMounted(() => {
  profileForm.value = { ...profileForm.value, ...props.store };
  loadCatalog();
});
</script>

<template>
  <main class="app-shell min-h-screen">
    <header class="site-header sticky top-0 z-30">
      <div
        class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4"
      >
        <div class="flex items-center gap-3">
          <span
            class="grid h-11 w-11 shrink-0 place-items-center bg-[#1e3d2b] text-white"
            style="border-radius: 8px"
            ><Store class="h-5 w-5"
          /></span>
          <div class="min-w-0">
            <p class="truncate text-lg font-semibold leading-6 text-ink">
              {{ store.name }}
            </p>
            <p class="truncate text-xs font-medium text-[#68635d]">
              Store Dashboard &middot; {{ store.category }}
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button class="secondary-button h-11 px-3" @click="emit('back')">
            <ArrowLeft class="h-4 w-4" /><span class="hidden sm:inline"
              >Back to Store</span
            ></button
          ><button
            class="secondary-button h-11 px-3"
            title="Logout"
            @click="emit('logout')"
          >
            <LogOut class="h-4 w-4" /><span class="hidden sm:inline"
              >Logout</span
            >
          </button>
        </div>
      </div>
    </header>

    <section
      class="mx-auto grid max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[240px_minmax(0,1fr)]"
    >
      <aside class="panel h-fit p-2">
        <nav class="space-y-1">
          <button
            v-for="section in sections"
            :key="section.key"
            class="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm font-semibold transition"
            style="border-radius: 8px"
            :class="
              activeSection === section.key
                ? 'bg-[#1e3d2b] text-white'
                : 'text-[#5e5953] hover:bg-field'
            "
            @click="activeSection = section.key"
          >
            <component :is="section.icon" class="h-4 w-4" />{{ section.label }}
          </button>
        </nav>
      </aside>

      <div class="panel min-h-[420px] p-6">
        <p
          v-if="error"
          class="mb-4 border border-ember bg-[#f8eae5] px-3 py-2 text-sm text-ember"
          style="border-radius: 8px"
        >
          {{ error }}
        </p>
        <p v-if="!canEdit" class="mb-4 border border-[#e4ece5] bg-[#f4efe6] px-3 py-2 text-sm text-[#1e3d2b]" style="border-radius: 8px">
          You have Viewer access. Dashboard data is read-only.
        </p>
        <p
          v-if="notice"
          class="mb-4 border border-moss bg-[#f4efe6] px-3 py-2 text-sm text-[#b3261e]"
          style="border-radius: 8px"
        >
          {{ notice }}
          <button class="float-right" @click="notice = ''">
            <X class="h-4 w-4" />
          </button>
        </p>

        <div v-if="activeSection === 'overview'">
          <h2 class="text-xl font-semibold">Ringkasan Toko</h2>
          <p class="mt-2 text-sm text-[#68635d]">
            {{ products.length }} produk dan {{ categories.length }} kategori
            aktif di tokomu.
          </p>
          <div class="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div class="border border-line bg-field p-4 r-panel">
              <p class="text-[11px] font-medium text-[#a09a92]">Pendapatan</p>
              <p class="mt-2 text-xl font-semibold" style="font-variant-numeric: tabular-nums">
                {{ formatIDR(analytics.total_sales) }}
              </p>
            </div>
            <div class="border border-line bg-field p-4 r-panel">
              <p class="text-[11px] font-medium text-[#a09a92]">Pesanan</p>
              <p class="mt-2 text-xl font-semibold" style="font-variant-numeric: tabular-nums">
                {{ analytics.order_count }}
              </p>
            </div>
            <div class="border border-line bg-field p-4 r-panel">
              <p class="text-[11px] font-medium text-[#a09a92]">Ulasan</p>
              <p class="mt-2 text-xl font-semibold" style="font-variant-numeric: tabular-nums">
                {{ storeReviews.review_count }}
              </p>
            </div>
            <div class="border border-line bg-field p-4 r-panel">
              <p class="text-[11px] font-medium text-[#a09a92]">
                Rating rata-rata
              </p>
              <p class="mt-2 text-xl font-semibold" style="font-variant-numeric: tabular-nums">
                {{ storeReviews.average_rating || "—" }} / 5
              </p>
            </div>
          </div>
          <div class="mt-6">
            <h3 class="font-semibold">Produk Terlaris</h3>
            <div
              v-if="topProducts.length"
              class="mt-3 divide-y divide-line border-y border-line"
            >
              <div
                v-for="item in topProducts.slice(0, 5)"
                :key="item.product_id"
                class="flex items-center gap-3 py-3 text-sm"
              >
                <div
                  class="grid h-11 w-11 shrink-0 place-items-center overflow-hidden bg-field r-ctl"
                >
                  <img
                    v-if="item.image_url"
                    :src="assetUrl(item.image_url)"
                    :alt="item.name"
                    class="h-full w-full object-cover"
                  />
                  <Package v-else class="h-5 w-5 text-[#a09a92]" />
                </div>
                <span class="min-w-0 flex-1 truncate font-medium">{{
                  item.name
                }}</span>
                <span class="shrink-0 text-[#68635d]" style="font-variant-numeric: tabular-nums"
                  >{{ item.units_sold }} unit ·
                  {{ formatIDR(item.revenue) }}</span
                >
              </div>
            </div>
            <p v-else class="py-4 text-sm text-[#68635d]">
              Belum ada penjualan.
            </p>
          </div>
        </div>

        <div v-else-if="activeSection === 'categories'">
          <h2 class="text-xl font-semibold">Manage Categories</h2>
          <form
            class="mt-4 flex items-end gap-2"
            @submit.prevent="saveCategory"
          >
            <label class="block flex-1 text-sm font-medium text-[#4d4944]"
              >Category name
              <input
                v-model="categoryName"
                class="w-full border border-line bg-field px-3 py-2 text-sm outline-none focus:border-moss"
                style="border-radius: 8px"
                maxlength="80"
                placeholder="Category name"
                required /></label
            ><div class="flex gap-2">
              <button class="primary-button" :disabled="busy">
                <Plus class="h-4 w-4" />{{ editingCategoryId ? "Save" : "Add" }}
              </button>
              <button v-if="editingCategoryId" type="button" class="secondary-button" @click="cancelCategoryEdit">
                Cancel
              </button>
            </div>
          </form>
          <div class="mt-5 divide-y divide-line border-y border-line">
            <div
              v-for="category in categories"
              :key="category.id"
              class="flex items-center justify-between py-3 text-sm"
            >
              <span>{{ category.name }}</span>
              <div class="flex items-center gap-3">
                <button class="text-forest" title="Edit category" @click="editCategory(category)">
                  Edit
                </button>
                <button class="icon-button text-ember" title="Delete category" @click="removeCategory(category)">
                  <Trash2 class="h-4 w-4" />
                </button>
              </div>
            </div>
            <p v-if="!categories.length" class="py-4 text-sm text-[#68635d]">
              No categories yet.
            </p>
          </div>
        </div>

        <div v-else-if="activeSection === 'discounts'">
          <h2 class="text-xl font-semibold">Manage Discounts</h2>
          <p class="mt-1 text-sm text-[#68635d]">
            Create promo codes with minimum spend and usage limits.
          </p>
          <form
            class="mt-4 grid gap-3 sm:grid-cols-2"
            @submit.prevent="saveDiscount"
          >
            <label class="block text-sm font-medium text-[#4d4944]"
              >Discount code
              <input
                v-model="discountForm.code"
                class="border border-line bg-field px-3 py-2 text-sm uppercase"
                style="border-radius: 8px"
                maxlength="40"
                placeholder="Code, e.g. SAVE10"
                required /></label
            ><label class="block text-sm font-medium text-[#4d4944]"
              >Discount type
              <select
                v-model="discountForm.kind"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
              >
                <option value="percentage">Percentage (%)</option>
                <option value="fixed">Fixed amount (Rp)</option>
              </select></label
            ><label class="block text-sm font-medium text-[#4d4944]"
              >Applies to
              <select
                v-model="discountForm.scope"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
              >
                <option value="all">All products</option>
                <option value="category">Product category</option>
                <option value="product">Specific product</option>
              </select></label
            ><label
              v-if="discountForm.scope === 'category'"
              class="block text-sm font-medium text-[#4d4944]"
              >Category target
              <select
                v-model="discountForm.target_id"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
                required
              >
                <option value="" disabled>Select a category</option>
                <option
                  v-for="category in categories"
                  :key="category.id"
                  :value="category.id"
                >
                  {{ category.name }}
                </option>
              </select></label
            ><label
              v-else-if="discountForm.scope === 'product'"
              class="block text-sm font-medium text-[#4d4944]"
              >Product target
              <select
                v-model="discountForm.target_id"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
                required
              >
                <option value="" disabled>Select a product</option>
                <option
                  v-for="product in products"
                  :key="product.id"
                  :value="product.id"
                >
                  {{ product.name }}
                </option>
              </select></label
            ><label class="block text-sm font-medium text-[#4d4944]"
              >Discount value
              <input
                v-model.number="discountForm.value"
                type="number"
                min="0.01"
                step="0.01"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
                placeholder="Discount value"
                required /></label
            ><label class="block text-sm font-medium text-[#4d4944]"
              >Minimum spend
              <input
                v-model.number="discountForm.min_subtotal"
                type="number"
                min="0"
                step="0.01"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
                placeholder="Minimum spend" /></label
            ><label class="block text-sm font-medium text-[#4d4944]"
              >Usage limit
              <input
                v-model.number="discountForm.usage_limit"
                type="number"
                min="1"
                step="1"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
                placeholder="Usage limit (optional)" /></label
            ><div class="flex gap-2 sm:col-span-2">
              <button class="primary-button" :disabled="busy">
                <Plus class="h-4 w-4" />{{ editingDiscountId ? "Save Changes" : "Create Discount" }}
              </button>
              <button v-if="editingDiscountId" type="button" class="secondary-button" @click="cancelDiscountEdit">
                Cancel
              </button>
            </div>
          </form>
          <div class="mt-6 divide-y divide-line border-y border-line">
            <div
              v-for="discount in discounts"
              :key="discount.id"
              class="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"
            >
              <div>
                <p class="font-semibold">
                  {{ discount.code }}
                  <span class="text-xs font-normal text-[#68635d]">{{
                    discount.kind === "percentage"
                      ? `${discount.value}%`
                      : formatIDR(discount.value)
                  }}</span>
                  <span class="ml-2 text-xs font-normal text-[#68635d]"
                    >({{
                      discount.scope === "category"
                        ? "Category"
                        : discount.scope === "product"
                          ? "Product"
                          : "All products"
                    }})</span
                  >
                </p>
                <p class="text-xs text-[#68635d]">
                  Used {{ discount.usage_count
                  }}{{
                    discount.usage_limit ? ` / ${discount.usage_limit}` : ""
                  }}
                  &middot; min. {{ formatIDR(discount.min_subtotal) }}
                </p>
              </div>
              <div class="flex flex-wrap gap-2">
                <button class="text-forest" @click="editDiscount(discount)">Edit</button>
                <button class="secondary-button" @click="toggleDiscount(discount)">
                  {{ discount.active ? "Deactivate" : "Activate" }}
                </button>
                <button class="text-ember" @click="removeDiscount(discount)">Delete</button>
              </div>
            </div>
            <p v-if="!discounts.length" class="py-4 text-sm text-[#68635d]">
              No discounts yet.
            </p>
          </div>
        </div>

        <div v-else-if="activeSection === 'products'">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h2 class="text-xl font-semibold">My Products</h2>
              <p class="mt-1 text-sm text-[#68635d]">
                Inventory is managed per product and validated at checkout.
              </p>
            </div>
            <div class="flex items-center gap-2">
              <button
                v-if="canEdit"
                class="secondary-button"
                :disabled="busy"
                @click="reconcileInventory"
              >
                Reconcile Inventory
              </button>
              <button
                v-if="editingProductId"
                class="secondary-button"
                @click="resetProduct"
              >
                Cancel edit
              </button>
            </div>
          </div>
          <form
            class="mt-5 grid gap-3 sm:grid-cols-2"
            @submit.prevent="saveProduct"
          >
            <label class="block text-sm font-medium text-[#4d4944]"
              >Product name
              <input
                v-model="productForm.name"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
                placeholder="Product name"
                required /></label
            ><label class="block text-sm font-medium text-[#4d4944]"
              >Price (Rp)
              <input
                v-model.number="productForm.price"
                type="number"
                min="0"
                step="0.01"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
                placeholder="Price"
                required /></label
            ><label
              class="block text-sm font-medium text-[#4d4944] sm:col-span-2"
              >Description
              <textarea
                v-model="productForm.description"
                class="sm:col-span-2 border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
                placeholder="Description"
                required
              ></textarea></label
            ><div class="block text-sm font-medium text-[#4d4944]"
              >Image URL
              <input
                v-model="productForm.image_url"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
                placeholder="Optional" />
              <div v-if="canEdit" class="mt-2 flex gap-2">
                <input
                  v-model="imageImportUrl"
                  type="url"
                  class="min-w-0 flex-1 border border-line bg-field px-3 py-2 text-sm"
                  style="border-radius: 8px"
                  placeholder="https://example.com/product.jpg"
                />
                <button type="button" class="secondary-button shrink-0" :disabled="imageImportBusy || !imageImportUrl.trim()" @click="importProductImage">
                  {{ imageImportBusy ? "Importing..." : "Import Image" }}
                </button>
              </div>
              <p v-if="imageImportError" class="mt-2 text-xs font-medium text-ember">{{ imageImportError }}</p>
              <img v-if="productForm.image_url" :src="assetUrl(productForm.image_url)" alt="Product preview" class="mt-2 h-24 w-24 object-cover" style="border-radius: 8px" />
            </div
            ><label class="block text-sm font-medium text-[#4d4944]"
              >SKU
              <input
                v-model="productForm.sku"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
                placeholder="Optional" /></label
            ><label class="block text-sm font-medium text-[#4d4944]"
              >Stock
              <input
                v-model.number="productForm.stock"
                type="number"
                min="0"
                step="1"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
                placeholder="Stock"
                required /></label
            ><label class="block text-sm font-medium text-[#4d4944]"
              >Status
              <select
                v-model="productForm.status"
                class="border border-line bg-field px-3 py-2 text-sm"
                style="border-radius: 8px"
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="archived">Archived</option>
              </select></label
            ><label
              class="block text-sm font-medium text-[#4d4944] sm:col-span-2"
              >Category
              <select
                v-model="productForm.category_id"
                class="border border-line bg-field px-3 py-2 text-sm sm:col-span-2"
                style="border-radius: 8px"
              >
                <option value="">No category</option>
                <option
                  v-for="category in categories"
                  :key="category.id"
                  :value="category.id"
                >
                  {{ category.name }}
                </option>
              </select></label
            ><button class="primary-button sm:col-span-2" :disabled="busy">
              {{ editingProductId ? "Save Changes" : "Add Product" }}
            </button>
          </form>
          <div
            v-if="products.length"
            class="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
          >
            <article
              v-for="product in products"
              :key="product.id"
              class="flex flex-col overflow-hidden border border-line bg-white r-panel"
            >
              <div class="relative aspect-[4/3] overflow-hidden bg-field">
                <img
                  v-if="product.image_url"
                  :src="assetUrl(product.image_url)"
                  :alt="product.name"
                  class="h-full w-full object-cover"
                />
                <div
                  v-else
                  class="grid h-full w-full place-items-center text-[#a09a92]"
                >
                  <Package class="h-8 w-8" />
                </div>
                <span
                  class="absolute left-3 top-3 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-white"
                  :style="{
                    borderRadius: '9999px',
                    backgroundColor:
                      product.status === 'active'
                        ? '#34694b'
                        : product.status === 'out-of-stock'
                          ? '#d84f2a'
                          : '#68635d',
                  }"
                >
                  {{ product.status }}
                </span>
              </div>
              <div class="flex min-w-0 flex-1 flex-col p-4">
                <p class="text-[11px] font-medium text-[#68635d]">
                  {{ product.category || "Tanpa kategori" }}
                </p>
                <h3 class="mt-1 line-clamp-3 text-sm font-semibold leading-5">
                  {{ product.name }}
                </h3>
                <p class="mt-1 line-clamp-3 text-xs leading-5 text-[#8b948d]">
                  {{ product.description }}
                </p>
                <div
                  class="mt-3 grid grid-cols-2 gap-2 border-t border-line pt-3 text-sm"
                >
                  <div>
                    <p class="text-[11px] text-[#a09a92]">Harga</p>
                    <p class="font-semibold text-forest">
                      {{ formatIDR(product.price) }}
                    </p>
                  </div>
                  <div>
                    <p class="text-[11px] text-[#a09a92]">Stok</p>
                    <p class="font-semibold">{{ product.stock }}</p>
                  </div>
                </div>
                <p
                  v-if="product.sku"
                  class="mt-2 text-[11px] text-[#8b948d]"
                >
                  SKU {{ product.sku }}
                </p>
                <div
                  class="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-3 text-xs font-semibold"
                >
                  <button class="text-forest" @click="editProduct(product)">
                    Edit
                  </button>
                  <button class="text-forest" @click="openVariants(product)">
                    Variants
                  </button>
                  <label class="inline-flex cursor-pointer items-center gap-1 text-forest"
                    ><Upload class="h-3.5 w-3.5" />Gambar<input
                      class="hidden"
                      type="file"
                      accept="image/jpeg,image/png,image/webp,image/gif"
                      @change="uploadProductImage(product, $event)" /></label
                  >
                  <button
                    class="ml-auto inline-flex items-center gap-1 text-ember"
                    @click="removeProduct(product)"
                  >
                    <Trash2 class="h-3.5 w-3.5" />Hapus
                  </button>
                </div>
              </div>
            </article>
          </div>
          <p
            v-else
            class="mt-6 rounded-2xl border border-dashed border-line p-10 text-center text-sm text-[#68635d]"
          >
            Belum ada produk. Tambahkan produk pertamamu lewat form di atas.
          </p>
          <div
            v-if="selectedVariantProduct"
            class="mt-6 border border-line p-4"
          >
            <div class="flex items-center justify-between">
              <h3 class="font-semibold">
                Variants: {{ selectedVariantProduct.name }}
              </h3>
              <button
                class="text-sm text-[#68635d]"
                @click="selectedVariantProduct = null"
              >
                Close
              </button>
            </div>
            <form
              class="mt-3 grid gap-2 sm:grid-cols-3"
              @submit.prevent="saveVariant"
            >
              <label class="block text-sm font-medium text-[#4d4944]"
                >Variant name
                <input
                  v-model="variantForm.name"
                  class="border border-line bg-field px-2 py-2 text-sm"
                  placeholder="Variant name"
                  required /></label
              ><label class="block text-sm font-medium text-[#4d4944]"
                >Size
                <input
                  v-model="variantForm.size"
                  class="border border-line bg-field px-2 py-2 text-sm"
                  placeholder="Size" /></label
              ><label class="block text-sm font-medium text-[#4d4944]"
                >Color
                <input
                  v-model="variantForm.color"
                  class="border border-line bg-field px-2 py-2 text-sm"
                  placeholder="Color" /></label
              ><label class="block text-sm font-medium text-[#4d4944]"
                >SKU
                <input
                  v-model="variantForm.sku"
                  class="border border-line bg-field px-2 py-2 text-sm"
                  placeholder="SKU"
                  required /></label
              ><label class="block text-sm font-medium text-[#4d4944]"
                >Stock
                <input
                  v-model.number="variantForm.stock"
                  type="number"
                  min="0"
                  class="border border-line bg-field px-2 py-2 text-sm"
                  placeholder="Stock"
                  required /></label
              ><label class="block text-sm font-medium text-[#4d4944]"
                >Price override (Rp)
                <input
                  v-model.number="variantForm.price"
                  type="number"
                  min="0"
                  step="0.01"
                  class="border border-line bg-field px-2 py-2 text-sm"
                  placeholder="Price override" /></label
              ><button class="primary-button sm:col-span-3" :disabled="busy">
                Add Variant
              </button>
            </form>
            <div class="mt-3 space-y-2 text-sm">
              <div
                v-for="variant in variants"
                :key="variant.id"
                class="flex justify-between border-t border-line pt-2"
              >
                <span>{{ variant.name }} &middot; {{ variant.sku }}</span
                ><span
                  >stock {{ variant.stock }} ·
                  {{
                    formatIDR(variant.price ?? selectedVariantProduct.price)
                  }}</span
                >
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="activeSection === 'orders'">
          <div class="flex items-center justify-between gap-3">
            <h2 class="text-xl font-semibold">Incoming Orders</h2>
            <div v-if="canEdit" class="flex flex-wrap gap-2">
              <button class="secondary-button" :disabled="busy" @click="exportOrders">
                Export Orders
              </button>
              <button class="secondary-button" :disabled="busy" @click="generateStoredExport">
                Generate Stored Export
              </button>
            </div>
          </div>
          <div class="mt-5 overflow-x-auto border-y border-line">
            <table class="w-full text-left text-sm">
              <thead>
                <tr
                  class="border-b border-line text-xs text-[#a09a92]"
                >
                  <th class="py-3 pr-3">Product</th>
                  <th class="py-3 pr-3">Buyer</th>
                  <th class="py-3 pr-3">Total</th>
                  <th class="py-3 pr-3">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="order in orders"
                  :key="order.id"
                  class="border-b border-line last:border-0"
                >
                  <td class="py-3 pr-3 font-semibold">
                    {{ order.product.name }} &times; {{ order.quantity }}
                  </td>
                  <td class="py-3 pr-3">#{{ order.buyer_id }}</td>
                  <td class="py-3 pr-3">
                    {{ formatIDR(order.total) }}
                  </td>
                  <td class="py-3 pr-3">
                    <div class="flex items-center gap-2">
                      <select
                        :value="order.status"
                        class="border border-line bg-field px-2 py-1 text-sm"
                        style="border-radius: 8px"
                        @change="updateOrder(order, $event.target.value)"
                      >
                        <option
                          v-for="status in [
                            'pending',
                            'confirmed',
                            'packed',
                            'shipped',
                            'completed',
                            'cancelled',
                          ]"
                          :key="status"
                          :value="status"
                        >
                          {{ status }}
                        </option>
                      </select>
                      <button
                        type="button"
                        class="secondary-button whitespace-nowrap"
                        @click="downloadInvoice(order.id)"
                      >
                        Download Invoice
                      </button>
                      <button
                        v-if="canEdit"
                        type="button"
                        class="secondary-button whitespace-nowrap"
                        :disabled="busy"
                        @click="viewPackingSlip(order)"
                      >
                        {{ packingSlips[order.id] ? "Hide Packing Slip" : "View Packing Slip" }}
                      </button>
                    </div>
                    <div
                      v-if="canEdit && packingSlips[order.id]"
                      class="mt-2 rounded-xl border border-line bg-[#ffffff] p-3 text-xs text-[#4d4944]"
                    >
                      <p><strong>Packing:</strong> {{ packingSlips[order.id].packing_status }}</p>
                      <p><strong>Warehouse bin:</strong> {{ packingSlips[order.id].warehouse_bin }}</p>
                      <p><strong>Batch:</strong> {{ packingSlips[order.id].fulfillment_batch }}</p>
                      <p><strong>Destination:</strong> {{ packingSlips[order.id].shipping_destination }}</p>
                    </div>
                    <div v-if="canEdit" class="mt-2 space-y-2">
                      <textarea
                        v-model="internalNoteDrafts[order.id]"
                        class="w-full border border-line bg-field px-2 py-1.5 text-sm"
                        maxlength="2000"
                        rows="2"
                        placeholder="Internal note for fulfillment"
                      ></textarea>
                      <button
                        type="button"
                        class="secondary-button"
                        :disabled="busy"
                        @click="saveInternalNote(order)"
                      >
                        Save Internal Note
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-if="!orders.length" class="py-4 text-sm text-[#68635d]">
              No orders for this store yet.
            </p>
          </div>
        </div>
        <div v-else-if="activeSection === 'reviews'">
          <div class="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 class="text-xl font-semibold">Store Reviews</h2>
              <p class="mt-2 text-sm text-[#68635d]">
                Customer feedback for your store products.
              </p>
            </div>
            <div class="flex gap-3">
              <div class="border border-line bg-field px-4 py-3">
                <p class="text-xs text-[#a09a92]">Reviews</p>
                <p class="mt-1 text-xl font-semibold">{{ storeReviews.review_count }}</p>
              </div>
              <div class="border border-line bg-field px-4 py-3">
                <p class="text-xs text-[#a09a92]">Average rating</p>
                <p class="mt-1 text-xl font-semibold">{{ storeReviews.average_rating || "—" }} / 5</p>
              </div>
            </div>
          </div>
          <div class="mt-5 space-y-3">
            <article
              v-for="review in storeReviews.items"
              :key="review.id"
              class="border border-line bg-white p-4"
            >
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p class="font-semibold">{{ review.product_name }}</p>
                  <p class="mt-1 text-xs text-[#68635d]">
                    {{ review.author_name }} · {{ review.created_at.slice(0, 10) }}
                  </p>
                </div>
                <div class="text-sm font-semibold text-[#a06b00]">
                  {{ review.rating }} / 5
                </div>
              </div>
              <div
                class="review-html mt-4 border-l-2 border-[#d7ead9] pl-4 text-sm leading-6 text-[#465149]"
              >{{ review.body }}</div>
            </article>
            <p
              v-if="!storeReviews.items.length"
              class="border border-dashed border-line py-8 text-center text-sm text-[#68635d]"
            >
              No reviews for this store yet.
            </p>
          </div>
        </div>
        <div v-else-if="activeSection === 'questions'">
          <h2 class="text-xl font-semibold">Product Q&A</h2>
          <div class="mt-4 flex gap-3">
            <button class="secondary-button" :aria-pressed="questionFilter === 'unanswered'" @click="questionFilter = 'unanswered'">Unanswered</button>
            <button class="secondary-button" :aria-pressed="questionFilter === 'answered'" @click="questionFilter = 'answered'">Answered</button>
          </div>
          <div class="mt-5 space-y-4">
            <article v-for="question in visibleQuestions" :key="question.id" class="border border-line bg-white p-4">
              <p class="font-semibold">{{ question.product_name }}</p>
              <p class="mt-1 text-xs text-[#68635d]">{{ question.customer_name }} · {{ question.created_at.slice(0, 10) }}</p>
              <!-- INTENTIONAL VULNERABILITY LAB: PRODUCT-QA-STORED-XSS -->
              <div class="mt-3 whitespace-pre-wrap" v-html="question.message"></div>
              <p v-if="question.answered_at" class="mt-3 whitespace-pre-wrap bg-[#eef5ef] p-3">{{ question.answer }}</p>
              <form v-if="canEdit" class="mt-3 space-y-2" @submit.prevent="answerQuestion(question)">
                <textarea v-model="answerDrafts[question.id]" class="w-full border border-line p-3" rows="3" maxlength="5000" required aria-label="Seller answer" placeholder="Write an answer" />
                <button class="primary-button" :disabled="busy">{{ question.answered_at ? 'Update Answer' : 'Answer' }}</button>
              </form>
            </article>
            <p v-if="!visibleQuestions.length" class="text-sm text-[#68635d]">No {{ questionFilter }} questions.</p>
          </div>
        </div>
        <div v-else-if="activeSection === 'analytics'">
          <h2 class="text-xl font-semibold">Penjualan</h2>
          <div class="mt-5 grid gap-3 sm:grid-cols-2">
            <div class="border border-line p-4 r-panel">
              <p class="text-[11px] font-medium text-[#a09a92]">Pendapatan</p>
              <p class="mt-2 text-2xl font-semibold" style="font-variant-numeric: tabular-nums">
                {{ formatIDR(analytics.total_sales) }}
              </p>
            </div>
            <div class="border border-line p-4 r-panel">
              <p class="text-[11px] font-medium text-[#a09a92]">Jumlah Pesanan</p>
              <p class="mt-2 text-2xl font-semibold" style="font-variant-numeric: tabular-nums">
                {{ analytics.order_count }}
              </p>
            </div>
          </div>
          <h3 class="mt-6 font-semibold">Produk Terlaris</h3>
          <div
            v-if="topProducts.length"
            class="mt-2 divide-y divide-line border-y border-line"
          >
            <div
              v-for="item in topProducts"
              :key="item.product_id"
              class="flex items-center gap-3 py-3 text-sm"
            >
              <div
                class="grid h-10 w-10 shrink-0 place-items-center overflow-hidden bg-field r-ctl"
              >
                <img
                  v-if="item.image_url"
                  :src="assetUrl(item.image_url)"
                  :alt="item.name"
                  class="h-full w-full object-cover"
                />
                <Package v-else class="h-5 w-5 text-[#a09a92]" />
              </div>
              <span class="min-w-0 flex-1 truncate font-medium">{{
                item.name
              }}</span>
              <span
                class="shrink-0 text-[#68635d]"
                style="font-variant-numeric: tabular-nums"
                >{{ item.units_sold }} unit ·
                {{ formatIDR(item.revenue) }}</span
              >
            </div>
          </div>
          <p v-else class="py-4 text-sm text-[#68635d]">
            Belum ada penjualan.
          </p>
        </div>
        <div v-else-if="activeSection === 'customers'">
          <h2 class="text-xl font-semibold">Customers</h2>
          <div class="mt-5 divide-y divide-line border-y border-line">
            <div
              v-for="customer in customers"
              :key="customer.id"
              class="flex justify-between py-3 text-sm"
            >
              <span
                ><!-- Intentional lab finding: customer display names are rendered as raw HTML. -->
                <span v-html="customer.display_name"></span>
                <span class="text-[#68635d]"
                  >@{{ customer.username }}</span
                ></span
              ><span
                >{{ customer.order_count }} orders ·
                {{ formatIDR(customer.total_spent) }}</span
              >
            </div>
            <p v-if="!customers.length" class="py-4 text-sm text-[#68635d]">
              No customers yet.
            </p>
          </div>
        </div>
        <div v-else-if="activeSection === 'settings'">
          <h2 class="text-xl font-semibold">Store Settings</h2>
          <form
            class="mt-5 grid gap-3 sm:grid-cols-2"
            @submit.prevent="saveProfile"
          >
            <label class="block text-sm font-medium text-[#4d4944]"
              >Store name
              <input
                v-model="profileForm.name"
                class="border border-line bg-field px-3 py-2 text-sm"
                placeholder="Store name"
                required /></label
            ><label class="block text-sm font-medium text-[#4d4944]"
              >Store category
              <input
                v-model="profileForm.category"
                class="border border-line bg-field px-3 py-2 text-sm"
                placeholder="Category store"
                required /></label
            ><label
              class="block text-sm font-medium text-[#4d4944] sm:col-span-2"
              >Description
              <textarea
                v-model="profileForm.description"
                class="sm:col-span-2 border border-line bg-field px-3 py-2 text-sm"
                placeholder="Description"
                required
              ></textarea></label
            ><label class="block text-sm font-medium text-[#4d4944]"
              >Address
              <input
                v-model="profileForm.address"
                class="border border-line bg-field px-3 py-2 text-sm"
                placeholder="Address" /></label
            ><label class="block text-sm font-medium text-[#4d4944]"
              >Phone
              <input
                v-model="profileForm.phone"
                class="border border-line bg-field px-3 py-2 text-sm"
                placeholder="Phone"
                required /></label
            ><label class="block text-sm font-medium text-[#4d4944] sm:col-span-2"
              >Opening hours
              <input
                v-model="profileForm.opening_hours"
                class="border border-line bg-field px-3 py-2 text-sm"
                placeholder="Opening hours" /></label
            ><div class="grid gap-3 sm:col-span-2 sm:grid-cols-2">
              <div class="upload-card flex h-full flex-col">
              <div class="flex min-h-[52px] items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-medium text-[#4d4944]">Store logo</p>
                  <p class="mt-1 text-xs text-[#8b948d]">PNG, JPG, WEBP, or GIF · max 5 MB</p>
                </div>
                <div class="upload-preview logo-preview">
                  <img v-if="profileForm.logo_url" :src="assetUrl(profileForm.logo_url)" alt="Store logo preview" />
                  <Upload v-else class="h-5 w-5" />
                </div>
              </div>
              <label class="upload-button mt-3">
                <Upload class="h-4 w-4" />
                <span>{{ storeFileNames.logo || (profileForm.logo_url ? "Replace logo" : "Choose logo") }}</span>
                <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" @change="uploadStoreImage('logo', $event)" />
              </label>
              </div>
              <div class="upload-card flex h-full flex-col">
              <div class="flex min-h-[52px] items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-medium text-[#4d4944]">Store banner</p>
                  <p class="mt-1 text-xs text-[#8b948d]">PNG, JPG, WEBP, or GIF · max 5 MB</p>
                </div>
                <div class="upload-preview banner-preview">
                  <img v-if="profileForm.banner_url" :src="assetUrl(profileForm.banner_url)" alt="Store banner preview" />
                  <Upload v-else class="h-5 w-5" />
                </div>
              </div>
              <label class="upload-button mt-3">
                <Upload class="h-4 w-4" />
                <span>{{ storeFileNames.banner || (profileForm.banner_url ? "Replace banner" : "Choose banner") }}</span>
                <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" @change="uploadStoreImage('banner', $event)" />
              </label>
              </div>
            </div
            ><label
              class="block text-sm font-medium text-[#4d4944] sm:col-span-2"
              >Return policy
              <textarea
                v-model="profileForm.return_policy"
                class="sm:col-span-2 border border-line bg-field px-3 py-2 text-sm"
                placeholder="Return policy"
              ></textarea></label
            ><button class="primary-button sm:col-span-2" :disabled="busy">
              Save Profile
            </button>
          </form>

          <section
            v-if="canEdit"
            class="mt-6 rounded-2xl border border-[#e1e9e1] bg-[#f8fbf8] p-4 sm:p-5"
          >
            <div>
              <h3 class="text-lg font-semibold">Email Preview</h3>
              <p class="mt-1 text-sm text-[#68635d]">
                Preview an order update email before sending it to a customer.
              </p>
            </div>

            <form class="mt-4 space-y-4" @submit.prevent="previewEmail">
              <label class="block text-sm font-medium text-[#4d4944]">
                Subject
                <input
                  v-model="emailPreviewForm.subject"
                  class="mt-2 w-full border border-line bg-white px-3 py-2.5 text-sm"
                  maxlength="200"
                  required
                />
              </label>
              <label class="block text-sm font-medium text-[#4d4944]">
                Body
                <textarea
                  v-model="emailPreviewForm.body"
                  class="mt-2 min-h-36 w-full border border-line bg-white px-3 py-2.5 text-sm"
                  maxlength="5000"
                  required
                ></textarea>
              </label>
              <button class="primary-button" :disabled="busy">
                Preview Email
              </button>
            </form>

            <div
              v-if="emailPreviewResult"
              class="mt-5 grid gap-4 border-t border-line pt-5"
            >
              <div>
                <p class="text-xs font-semibold text-[#68635d]">
                  Rendered Subject
                </p>
                <p class="mt-2 rounded-xl border border-line bg-white p-3 text-sm">
                  {{ emailPreviewResult.subject }}
                </p>
              </div>
              <div>
                <p class="text-xs font-semibold text-[#68635d]">
                  Rendered Body
                </p>
                <pre class="mt-2 whitespace-pre-wrap rounded-xl border border-line bg-white p-3 text-sm">{{ emailPreviewResult.body }}</pre>
              </div>
            </div>
          </section>
        </div>

        <div v-else-if="activeSection === 'webhook'">
          <h2 class="text-xl font-semibold">Webhook Settings</h2>
          <p class="mt-1 text-sm text-[#68635d]">Configure Discord notifications for new orders in your store.</p>
          <section class="mt-5">
            <div class="rounded-2xl border border-[#e1e9e1] bg-[#f8fbf8] p-4 sm:p-5">
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#f4efe6] text-[#b3261e]">
                      <MessageSquare class="h-4 w-4" />
                    </div>
                    <div>
                      <h3 class="text-lg font-semibold leading-tight">Discord Webhook</h3>
                      <p class="mt-1 text-sm text-[#68635d]">Get notified when your store receives a new order.</p>
                    </div>
                  </div>
                </div>
                <span v-if="webhook?.active" class="shrink-0 rounded-full bg-[#e4f6e7] px-3 py-1 text-xs font-semibold text-forest">Active</span>
                <span v-else-if="webhook" class="shrink-0 rounded-full bg-[#fff0eb] px-3 py-1 text-xs font-semibold text-ember">Inactive</span>
              </div>

              <form v-if="canEdit" class="mt-5 rounded-xl border border-line bg-white p-4" @submit.prevent="saveWebhook">
                <div class="grid gap-4 lg:grid-cols-[minmax(180px,0.6fr)_minmax(0,1.4fr)]">
                  <label class="block text-sm font-medium text-[#4d4944]"><span>Webhook name</span><input v-model="webhookForm.name" class="mt-2 w-full border border-line bg-field px-3 py-2.5 text-sm" placeholder="Discord notifications" required /></label>
                  <label class="block text-sm font-medium text-[#4d4944]"><span>Discord webhook URL</span><input v-model="webhookForm.url" type="url" class="mt-2 w-full border border-line bg-field px-3 py-2.5 text-sm" placeholder="https://discord.com/api/webhooks/..." required /><span class="mt-1.5 block text-xs font-normal text-[#8b948d]">Only Discord webhook URLs can be saved.</span></label>
                </div>
                <div class="mt-4 flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-between">
                  <p class="text-xs text-[#8b948d]">Send order updates to Discord.</p>
                  <div class="flex flex-wrap gap-2">
                    <label title="Enable notifications" class="flex h-[42px] w-[42px] cursor-pointer items-center justify-center rounded-xl border border-line bg-field"><input v-model="webhookForm.active" type="checkbox" class="h-4 w-4 accent-moss" aria-label="Enable notifications" /></label>
                    <button type="button" class="secondary-button" :disabled="busy || !webhookForm.url.trim()" @click="webhookTestUrl = webhookForm.url; testWebhook()">Test</button>
                    <button class="primary-button" :disabled="busy">Save</button>
                    <button v-if="webhook" type="button" class="secondary-button text-ember" @click="deleteWebhook">Delete</button>
                  </div>
                </div>
              </form>
              <p v-else class="mt-5 rounded-xl border border-line bg-white px-4 py-3 text-sm text-[#68766c]">Viewer access is read-only.</p>

              <div v-if="canEdit" class="mt-4 rounded-xl border border-[#e4ece5] bg-white p-4">
                <div class="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-4"><div><h4 class="font-semibold">Test response</h4><p class="mt-1 text-xs leading-5 text-[#68635d]">Inspect the latest response from the URL tested above, including its status, headers, and body.</p></div><span class="w-fit rounded-full bg-[#fff6df] px-2.5 py-1 text-[11px] font-semibold text-[#8a681d]">Developer tool</span></div>
                <div v-if="webhookTestResult" class="mt-4 grid gap-3 lg:grid-cols-2">
                  <div class="rounded-xl border border-line bg-[#f8fbf8] p-3 lg:col-span-2"><p class="text-xs font-semibold text-[#68635d]">Status code</p><p class="mt-1 text-xl font-semibold" :class="webhookTestResult.status_code && webhookTestResult.status_code < 400 ? 'text-forest' : 'text-ember'">{{ webhookTestResult.status_code ?? "Request failed" }}</p></div>
                  <div><p class="text-xs font-semibold text-[#68635d]">Response headers</p><pre class="mt-2 max-h-48 overflow-auto rounded-xl bg-[#163021] p-3 text-xs leading-5 text-white">{{ JSON.stringify(webhookTestResult.headers, null, 2) }}</pre></div>
                  <div><p class="text-xs font-semibold text-[#68635d]">Response body</p><pre class="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-xl bg-[#163021] p-3 text-xs leading-5 text-white">{{ webhookTestResult.body }}</pre></div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <div v-else-if="activeSection === 'media'">
          <h2 class="text-xl font-semibold">Media Manager</h2>
          <p class="mt-1 text-sm text-[#68635d]">Preview uploaded store and product files.</p>

          <div class="mt-5 rounded-2xl border border-[#e1e9e1] bg-[#f8fbf8] p-4 sm:p-5">
            <div class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
              <label class="block min-w-0 flex-1 text-sm font-medium text-[#4d4944]">
                <span>File path</span>
                <input v-model="mediaPath" class="mt-2 w-full border border-line bg-white px-3 py-2.5 text-sm" placeholder="stores/example.png" />
                <span class="mt-1.5 block text-xs font-normal text-[#8b948d]">Use a path from the list below to preview a file.</span>
              </label>
              <button type="button" class="primary-button h-[42px] shrink-0 sm:mt-[26px]" :disabled="busy || !mediaPath.trim()" @click="previewMedia()">Preview file</button>
            </div>

            <div class="mt-5 overflow-hidden rounded-xl border border-line bg-white">
              <div class="border-b border-line px-4 py-3">
                <h3 class="text-sm font-semibold">Uploaded files</h3>
              </div>
              <div v-if="media.length" class="divide-y divide-line">
                <div v-for="item in media" :key="`${item.type}-${item.path}`" class="flex flex-col gap-2 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                  <div class="min-w-0">
                    <p class="truncate font-medium text-ink">{{ item.name }}</p>
                    <p class="truncate text-xs text-[#8b948d]">{{ item.type }}<span v-if="item.product_name"> · {{ item.product_name }}</span></p>
                  </div>
                  <button type="button" class="secondary-button shrink-0" @click="mediaPath = item.path; previewMedia(item.path)">Preview</button>
                </div>
              </div>
              <p v-else class="px-4 py-5 text-sm text-[#68635d]">No uploaded files found.</p>
            </div>

            <div v-if="mediaPreview" class="mt-4 rounded-xl border border-line bg-white p-4">
              <div class="flex items-center justify-between gap-3">
                <div class="min-w-0"><p class="text-xs font-semibold text-[#68635d]">Preview</p><p class="mt-1 truncate text-sm font-medium">{{ mediaPreview.name }}</p></div>
                <span class="shrink-0 text-xs text-[#8b948d]">{{ mediaPreview.contentType }}</span>
              </div>
              <img v-if="mediaPreview.contentType.startsWith('image/')" :src="mediaPreview.url" alt="Media preview" class="mt-3 max-h-72 w-full rounded-lg bg-field object-contain" />
              <iframe v-else :src="mediaPreview.url" title="File preview" class="mt-3 h-72 w-full rounded-lg border border-line bg-white"></iframe>
            </div>
          </div>
        </div>

        <div v-else-if="activeSection === 'team'">
          <h2 class="text-xl font-semibold">Team</h2>
          <p class="mt-1 text-sm text-[#68635d]">Create local team accounts with read-only Viewer or editable Editor access.</p>
          <form v-if="isOwner" class="mt-5 grid gap-3 sm:grid-cols-2" @submit.prevent="saveTeamMember">
            <label class="block text-sm font-medium text-[#4d4944]">Username<input v-model="teamForm.username" class="border border-line bg-field px-3 py-2 text-sm" required /></label>
            <label class="block text-sm font-medium text-[#4d4944]">Display name<input v-model="teamForm.display_name" class="border border-line bg-field px-3 py-2 text-sm" required /></label>
            <label class="block text-sm font-medium text-[#4d4944]">Password<input v-model="teamForm.password" type="password" minlength="8" class="border border-line bg-field px-3 py-2 text-sm" required /></label>
            <label class="block text-sm font-medium text-[#4d4944]">Role<select v-model="teamForm.role" class="border border-line bg-field px-3 py-2 text-sm"><option value="viewer">Viewer</option><option value="editor">Editor</option></select></label>
            <button class="primary-button sm:col-span-2" :disabled="busy"><Plus class="h-4 w-4" />Create Team Account</button>
          </form>
          <p v-else class="mt-5 rounded-xl border border-line bg-field px-4 py-3 text-sm text-[#68766c]">Only the store owner can create team accounts.</p>
          <div class="mt-6 overflow-x-auto border-y border-line">
            <table class="w-full text-left text-sm">
              <thead>
                <tr class="border-b border-line text-xs text-[#a09a92]">
                  <th class="py-3 pr-3">Username</th>
                  <th class="py-3 pr-3">Display name</th>
                  <th class="py-3 pr-3">Role</th>
                  <th class="py-3 pr-3">Status</th>
                  <th class="py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="member in teamMembers" :key="member.id" class="border-b border-line last:border-0">
                  <td class="py-3 pr-3">{{ member.username }}</td>
                  <td class="py-3 pr-3">{{ member.display_name }}</td>
                  <td class="py-3 pr-3">
                    <select v-if="isOwner" :value="member.role" class="border border-line bg-field px-2 py-1 text-xs" @change="updateTeamMember(member, { role: $event.target.value })">
                      <option value="viewer">Viewer</option>
                      <option value="editor">Editor</option>
                    </select>
                    <span v-else class="capitalize">{{ member.role }}</span>
                  </td>
                  <td class="py-3 pr-3">
                    <span :class="member.active ? 'text-forest' : 'text-ember'">{{ member.active ? "Active" : "Inactive" }}</span>
                  </td>
                  <td class="py-3">
                    <div v-if="isOwner" class="flex flex-wrap gap-2">
                      <button class="text-forest" @click="updateTeamMember(member, { active: !member.active })">
                        {{ member.active ? "Deactivate" : "Activate" }}
                      </button>
                      <button class="text-forest" @click="resetTeamPassword(member)">Reset password</button>
                      <button class="text-ember" @click="removeTeamMember(member)">Remove</button>
                    </div>
                    <span v-else class="text-[#68635d]">Read only</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-if="!teamMembers.length" class="py-4 text-sm text-[#68635d]">No team accounts yet.</p>
          </div>
        </div>

        <div
          v-if="activeSection !== 'products' && activeSection !== 'categories'"
          class="mt-6 border-t border-line pt-6 text-sm text-[#68635d]"
        >
          <p class="font-semibold text-ink">Store Details</p>
          <dl class="mt-3 grid gap-2 sm:grid-cols-2">
            <div>
              <dt class="text-xs text-[#a09a92]">
                Description
              </dt>
              <dd>{{ store.description }}</dd>
            </div>
            <div>
              <dt class="text-xs text-[#a09a92]">
                City
              </dt>
              <dd>{{ store.city }}</dd>
            </div>
            <div>
              <dt class="text-xs text-[#a09a92]">
                Phone
              </dt>
              <dd>{{ store.phone }}</dd>
            </div>
            <div>
              <dt class="text-xs text-[#a09a92]">
                Store URL
              </dt>
              <dd>/stores/{{ store.slug }}</dd>
            </div>
          </dl>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
form > label {
  width: 100%;
}

form input:not([type="file"]),
form select,
form textarea {
  box-sizing: border-box;
  display: block;
  width: 100%;
  min-height: 42px;
  margin-top: 0.5rem;
}

form textarea {
  min-height: 104px;
  resize: vertical;
}

.upload-card {
  min-width: 0;
  border: 1px solid #dce8df;
  border-radius: 12px;
  padding: 1rem;
  background: #ffffff;
}

.upload-preview {
  display: grid;
  place-items: center;
  overflow: hidden;
  flex: 0 0 auto;
  color: #b3261e;
  background: #f4efe6;
  border-radius: 10px;
}

.logo-preview {
  width: 52px;
  height: 52px;
}

.banner-preview {
  width: 92px;
  height: 52px;
}

.upload-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.upload-button {
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  border: 1px solid #b7dfbd;
  border-radius: 8px;
  padding: 0.6rem 0.8rem;
  width: 100%;
  justify-content: center;
  color: #b3261e;
  background: white;
  font-size: 0.8rem;
  font-weight: 600;
  transition: background 150ms ease, border-color 150ms ease;
}

.upload-button:hover {
  border-color: #b3261e;
  background: #f4efe6;
}

.upload-button input[type="file"] {
  display: none;
}
</style>

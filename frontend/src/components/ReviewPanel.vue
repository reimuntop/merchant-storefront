<script setup>
import { computed, onMounted, ref, watch } from "vue";
import {
  BadgeCheck,
  EyeOff,
  Send,
  ShoppingBag,
  Star,
} from "lucide-vue-next";
import { request } from "../api";

const props = defineProps({
  product: { type: Object, required: true },
  userId: { type: Number, required: true },
  canReview: { type: Boolean, required: true },
});
const emit = defineEmits(["changed"]);

const reviews = ref([]);
const rating = ref(5);
const body = ref("");
const isAnonymous = ref(false);
const loading = ref(false);
const averageRating = computed(() =>
  reviews.value.length
    ? (
        reviews.value.reduce((sum, review) => sum + review.rating, 0) /
        reviews.value.length
      ).toFixed(1)
    : "—",
);
const hasReviewed = computed(() =>
  reviews.value.some((review) => review.user_id === props.userId),
);

async function loadReviews() {
  if (!props.product) return;
  reviews.value = await request(`/api/products/${props.product.id}/reviews`);
}

async function addReview() {
  if (!props.canReview || hasReviewed.value || !body.value.trim()) return;
  loading.value = true;
  try {
    await request("/api/reviews", {
      method: "POST",
      body: JSON.stringify({
        product_id: props.product.id,
        rating: rating.value,
        body: body.value,
        user_id: props.userId,
        is_anonymous: isAnonymous.value,
      }),
    });
    body.value = "";
    isAnonymous.value = false;
    await loadReviews();
    emit("changed");
  } finally {
    loading.value = false;
  }
}

watch(() => props.product.id, loadReviews);
onMounted(loadReviews);
</script>

<template>
  <section class="panel overflow-hidden">
    <div
      class="border-b border-line bg-gradient-to-r from-[#f4efe6] via-white to-white px-5 py-5 sm:px-6"
    >
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p class="text-[#1e3d2b]">
            Customer feedback
          </p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight">
            Reviews for {{ product.name }}
          </h2>
          <p class="mt-1 text-sm text-[#1e3d2b]">
            Real notes from verified buyers.
          </p>
        </div>
        <div
          class="flex items-center gap-3 rounded-2xl border border-white bg-white/80 px-4 py-3 shadow-sm"
        >
          <div class="flex items-center gap-1">
            <Star
              v-for="star in 5"
              :key="star"
              class="h-4 w-4"
              :class="
                star <= Math.round(Number(averageRating) || 0)
                  ? 'fill-[#f0b429] text-[#f0b429]'
                  : 'text-[#d2d9d3]'
              "
            />
          </div>
          <div>
            <p class="text-lg font-bold leading-5 text-ink">
              {{ averageRating }}
            </p>
            <p class="text-[11px] text-[#1e3d2b]">
              {{ reviews.length }}
              {{ reviews.length === 1 ? "review" : "reviews" }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <div class="grid gap-6 p-5 sm:p-6 lg:grid-cols-[minmax(0,1fr)_350px]">
      <div>
        <div
          v-if="!reviews.length"
          class="grid min-h-40 place-items-center rounded-2xl border border-dashed border-line bg-[#ffffff] p-6 text-center"
        >
          <div>
            <div
              class="mx-auto grid h-11 w-11 place-items-center rounded-2xl bg-[#f4efe6] text-[#1e3d2b]"
            >
              <Star class="h-5 w-5" />
            </div>
            <p class="mt-3 font-semibold text-ink">No reviews yet</p>
            <p class="mt-1 text-sm text-[#1e3d2b]">
              Be the first buyer to share your experience.
            </p>
          </div>
        </div>
        <div v-else class="space-y-3">
          <article
            v-for="review in reviews"
            :key="review.id"
            class="rounded-2xl border border-line bg-white p-4 transition hover:border-[#b7dfbd] hover:shadow-sm sm:p-5"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex min-w-0 items-start gap-3">
                <div
                  class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#f4efe6] text-sm font-bold text-[#1e3d2b]"
                >
                  {{
                    (review.author_name || `User #${review.user_id}`)
                      .slice(0, 1)
                      .toUpperCase()
                  }}
                </div>
                <div class="min-w-0">
                  <p class="truncate font-semibold text-ink">
                    {{ review.author_name || `User #${review.user_id}` }}
                  </p>
                  <div class="mt-1 flex items-center gap-2">
                    <span class="flex items-center gap-0.5"
                      ><Star
                        v-for="star in 5"
                        :key="star"
                        class="h-3.5 w-3.5"
                        :class="
                          star <= review.rating
                            ? 'fill-[#f0b429] text-[#f0b429]'
                            : 'text-[#d2d9d3]'
                        " /></span
                    ><span
                      v-if="review.is_anonymous"
                      class="inline-flex items-center gap-1 text-[11px] font-medium text-[#1e3d2b]"
                      ><EyeOff class="h-3.5 w-3.5" />Anonymous</span
                    >
                  </div>
                </div>
              </div>
            </div>
            <div
              class="review-html mt-4 whitespace-pre-wrap border-l-2 border-[#d7ead9] pl-4 text-sm leading-6 text-[#465149]"
            >{{ review.body }}</div>
          </article>
        </div>
      </div>

      <form
        v-if="canReview && !hasReviewed"
        class="rounded-2xl border border-[#cfe6d2] bg-[#f7fcf7] p-5"
        @submit.prevent="addReview"
      >
        <div class="flex items-start gap-3">
          <div
            class="grid h-10 w-10 place-items-center rounded-xl bg-forest text-white"
          >
            <Send class="h-4 w-4" />
          </div>
          <div>
            <h3 class="font-semibold text-ink">Share your experience</h3>
            <p class="mt-1 text-xs leading-5 text-[#1e3d2b]">
              Your review helps other shoppers decide.
            </p>
          </div>
        </div>
        <label
          class="mt-5 block text-xs text-[#1e3d2b]"
          for="rating"
          >Your rating</label
        >
        <div class="mt-2 flex items-center gap-3">
          <input
            id="rating"
            v-model.number="rating"
            type="range"
            min="1"
            max="5"
            class="w-full accent-moss"
          /><span
            class="min-w-12 rounded-lg bg-white px-2 py-1 text-center text-sm font-bold text-forest shadow-sm"
            >{{ rating }}/5</span
          >
        </div>
        <div class="mt-2 flex gap-1">
          <Star
            v-for="star in 5"
            :key="star"
            class="h-5 w-5"
            :class="
              star <= rating
                ? 'fill-[#f0b429] text-[#f0b429]'
                : 'text-[#d2d9d3]'
            "
          />
        </div>
        <label
          class="mt-5 block text-xs text-[#1e3d2b]"
          for="review-body"
          >Your review</label
        >
        <textarea
          id="review-body"
          v-model="body"
          rows="6"
          class="mt-2 w-full resize-none border border-line bg-white p-3 text-sm outline-none focus:border-moss"
          placeholder="Share fit, quality, delivery, setup, or daily-use details..."
        />
        <label
          class="mt-4 flex cursor-pointer items-center gap-2 text-sm font-medium text-[#4d5950]"
          ><input
            v-model="isAnonymous"
            type="checkbox"
            class="h-4 w-4 accent-moss"
          />Post anonymously</label
        >
        <p class="mt-3 rounded-lg border border-[#e4ece5] bg-white px-3 py-2 text-xs leading-5 text-[#1e3d2b]">
          Reviews cannot be deleted after submission.
        </p>
        <button
          class="primary-button mt-5 w-full py-3"
          :disabled="loading || !body.trim()"
        >
          <Send class="h-4 w-4" />{{
            loading ? "Submitting..." : "Submit review"
          }}
        </button>
      </form>
      <div
        v-else-if="hasReviewed"
        class="relative overflow-hidden rounded-2xl border border-[#e4ece5] bg-gradient-to-br from-[#f2fbf3] via-white to-[#fffdf5] p-5"
      >
        <div class="relative grid h-12 w-12 place-items-center rounded-2xl bg-forest text-white shadow-sm">
          <BadgeCheck class="h-5 w-5" />
        </div>
        <h3 class="relative mt-5 font-semibold text-ink">You already reviewed this product</h3>
        <p class="relative mt-2 text-sm leading-6 text-[#68766c]">Each verified buyer can submit one review per product.</p>
      </div>
      <div
        v-else
        class="relative overflow-hidden rounded-2xl border border-[#e4ece5] bg-gradient-to-br from-[#f2fbf3] via-white to-[#fffdf5] p-5"
      >
        <div
          class="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-[#dff3e1]"
        ></div>
        <div
          class="relative grid h-12 w-12 place-items-center rounded-2xl bg-forest text-white shadow-sm"
        >
          <ShoppingBag class="h-5 w-5" />
        </div>
        <div class="relative mt-5 flex items-center gap-2">
          <h3 class="font-semibold text-ink">You cannot review this product yet</h3>
          <BadgeCheck class="h-4 w-4 text-moss" />
        </div>
        <p class="relative mt-2 text-sm leading-6 text-[#68766c]">
          Purchase and complete an order for this product before sharing your
          experience.
        </p>
        <div
          class="relative mt-5 flex items-start gap-2 rounded-xl bg-white/80 p-3 text-xs leading-5 text-[#68766c] shadow-sm"
        >
          <BadgeCheck class="mt-0.5 h-4 w-4 shrink-0 text-moss" /><span
            >Reviews are only available to verified buyers to keep feedback
            trustworthy.</span
          >
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ShoppingCart, Star } from "lucide-vue-next";
import { formatIDR } from "../formatters";

defineProps({
  product: { type: Object, required: true },
  selected: { type: Boolean, default: false },
});

defineEmits(["select", "add"]);
</script>

<template>
  <article
    class="panel group relative flex h-full flex-row overflow-hidden"
    :class="selected ? 'ring-2 ring-moss ring-offset-2' : ''"
  >
    <button class="flex w-full items-stretch text-left" @click="$emit('select')">
      <div class="relative w-28 shrink-0 self-stretch overflow-hidden bg-field">
        <img
          :src="product.image_url"
          :alt="product.name"
          class="absolute inset-0 h-full w-full object-cover"
        />
        <span
          v-if="product.status === 'out-of-stock'"
          class="absolute left-0 top-0 bg-ember px-2 py-0.5 text-[10px] font-bold text-white"
          >Habis</span
        >
      </div>
      <div class="flex min-w-0 flex-1 flex-col p-3">
        <p class="text-[11px] font-medium text-[#68635d]">{{ product.category }}</p>
        <h3 class="mt-0.5 line-clamp-2 text-sm font-semibold leading-5">{{ product.name }}</h3>
        <p class="mt-1.5 line-clamp-2 text-[11px] leading-4 text-[#8b948d]">{{ product.description }}</p>
        <p class="mt-auto flex items-end justify-between gap-2 pt-2">
          <span class="text-base font-bold text-forest">{{ formatIDR(product.price) }}</span>
          <button
            class="grid h-9 w-9 shrink-0 place-items-center bg-forest text-white transition hover:bg-[#163021] r-ctl"
            :disabled="product.status === 'out-of-stock'"
            :title="product.status === 'out-of-stock' ? 'Stok habis' : 'Tambah ke keranjang'"
            @click="$emit('add')"
          >
            <ShoppingCart class="h-4 w-4" />
          </button>
        </p>
        <p class="mt-0.5 flex items-center gap-1 text-[11px] text-[#68635d]">
          <Star class="h-3.5 w-3.5 fill-[#f0b429] text-[#f0b429]" />
          {{ product.status === "out-of-stock" ? "Stok habis" : "Siap dikirim" }}
        </p>
      </div>
    </button>
  </article>
</template>

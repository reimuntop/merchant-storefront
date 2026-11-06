const idrFormatter = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

function formatIDR(value) {
  return idrFormatter.format(Number(value) || 0).replace("IDR", "Rp");
}

export { formatIDR };

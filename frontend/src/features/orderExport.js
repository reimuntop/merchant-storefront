import { API_BASE, getStoredUser } from "../api";

const storeRoute = ["api", "stores", "me"];
const exportOperation = ["orders", "export"];
const generatedExportsOperation = ["exports"];

async function downloadOrderExport() {
  const session = getStoredUser();
  const endpoint = `/${[...storeRoute, ...exportOperation].join("/")}`;
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: session?.access_token
      ? { Authorization: `Bearer ${session.access_token}` }
      : {},
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to export orders (${response.status}): ${message}`);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "orders-export.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function generateAndDownloadOrderExport() {
  const session = getStoredUser();
  const exportsEndpoint = `/${[...storeRoute, ...generatedExportsOperation].join("/")}`;
  const authHeaders = session?.access_token
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};
  const createResponse = await fetch(`${API_BASE}${exportsEndpoint}`, {
    method: "POST",
    headers: authHeaders,
  });
  if (!createResponse.ok) {
    const message = await createResponse.text();
    throw new Error(`Failed to generate export (${createResponse.status}): ${message}`);
  }

  const artifact = await createResponse.json();
  const downloadResponse = await fetch(`${API_BASE}${exportsEndpoint}/${artifact.id}`, {
    headers: authHeaders,
  });
  if (!downloadResponse.ok) {
    const message = await downloadResponse.text();
    throw new Error(`Failed to download generated export (${downloadResponse.status}): ${message}`);
  }

  const blob = await downloadResponse.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = artifact.filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return artifact;
}

export { downloadOrderExport, generateAndDownloadOrderExport };

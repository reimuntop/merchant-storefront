const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const AUTH_STORAGE_KEY = "prompt-injection-shop-user";

async function request(path, options = {}) {
  const session = getStoredUser();
  const { headers: optionHeaders, ...fetchOptions } = options;
  const headers = { ...(optionHeaders || {}) };
  if (!(fetchOptions.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (session?.access_token && !headers.Authorization) {
    headers.Authorization = `Bearer ${session.access_token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers,
  });
  if (response.status === 401 && session?.access_token) {
    clearStoredUser();
    window.dispatchEvent(new CustomEvent("auth:unauthorized"));
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

function getStoredUser() {
  try {
    const user = JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY));
    return user?.access_token ? user : null;
  } catch {
    return null;
  }
}

function storeUser(user) {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
}

function clearStoredUser() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

function assetUrl(path) {
  if (!path) return "";
  if (/^(https?:)?\/\//i.test(path)) return path;
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export { API_BASE, assetUrl, clearStoredUser, getStoredUser, request, storeUser };

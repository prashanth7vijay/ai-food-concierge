const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* response wasn't JSON — keep the generic message */
    }
    const error = new Error(detail);
    error.status = res.status;
    throw error;
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  sendChatMessage({ userId, conversationId, message }) {
    return request("/chat", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, conversation_id: conversationId, message }),
    });
  },

  getPreferences(userId) {
    return request(`/preferences?user_id=${userId}`);
  },

  updatePreferences(userId, update) {
    return request(`/preferences?user_id=${userId}`, {
      method: "PUT",
      body: JSON.stringify(update),
    });
  },

  compareItems(itemIds) {
    return request("/compare", {
      method: "POST",
      body: JSON.stringify({ item_ids: itemIds }),
    });
  },

  saveItem(userId, menuItemId) {
    return request("/saved-items", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, menu_item_id: menuItemId }),
    });
  },

  listSavedItems(userId) {
    return request(`/saved-items?user_id=${userId}`);
  },

  removeSavedItem(savedItemId) {
    return request(`/saved-items/${savedItemId}`, { method: "DELETE" });
  },
};

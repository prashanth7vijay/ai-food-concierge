import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

const AppStateContext = createContext(null);

const USER_ID_KEY = "food-concierge-user-id";

function getOrCreateUserId() {
  let id = localStorage.getItem(USER_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(USER_ID_KEY, id);
  }
  return id;
}

export function AppStateProvider({ children }) {
  const [userId] = useState(getOrCreateUserId);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [activity, setActivity] = useState([]);
  const [preferences, setPreferences] = useState(null);
  const [savedItems, setSavedItems] = useState([]);
  const [compareIds, setCompareIds] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState(null);

  const refreshPreferences = useCallback(async () => {
    try {
      const prefs = await api.getPreferences(userId);
      setPreferences(prefs);
    } catch {
      /* preferences are supplementary — a failed refresh shouldn't break chat */
    }
  }, [userId]);

  const refreshSavedItems = useCallback(async () => {
    try {
      const { items } = await api.listSavedItems(userId);
      setSavedItems(items);
    } catch {
      /* non-critical */
    }
  }, [userId]);

  useEffect(() => {
    refreshPreferences();
    refreshSavedItems();
  }, [refreshPreferences, refreshSavedItems]);

  const sendMessage = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed) return;

      setMessages((prev) => [...prev, { role: "user", content: trimmed, id: crypto.randomUUID() }]);
      setIsSending(true);
      setChatError(null);
      setActivity([]);

      try {
        const response = await api.sendChatMessage({
          userId,
          conversationId,
          message: trimmed,
        });
        setConversationId(response.conversation_id);
        setActivity(response.activity || []);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: response.reply,
            id: response.agent_run_id,
            recommendations: response.recommendations || [],
            intent: response.intent,
            errors: response.errors || [],
          },
        ]);
        if (response.preferences) setPreferences(response.preferences);
      } catch (err) {
        setChatError(err.message || "Something went wrong reaching the concierge.");
      } finally {
        setIsSending(false);
      }
    },
    [userId, conversationId]
  );

  const toggleCompare = useCallback((itemId) => {
    setCompareIds((prev) => {
      if (prev.includes(itemId)) return prev.filter((id) => id !== itemId);
      if (prev.length >= 3) return prev; // keep the tray small and legible
      return [...prev, itemId];
    });
  }, []);

  const clearCompare = useCallback(() => setCompareIds([]), []);

  const saveItem = useCallback(
    async (itemId) => {
      await api.saveItem(userId, itemId);
      refreshSavedItems();
    },
    [userId, refreshSavedItems]
  );

  const removeSavedItem = useCallback(
    async (savedItemId) => {
      await api.removeSavedItem(savedItemId);
      refreshSavedItems();
    },
    [refreshSavedItems]
  );

  const value = useMemo(
    () => ({
      userId,
      conversationId,
      messages,
      activity,
      preferences,
      savedItems,
      compareIds,
      isSending,
      chatError,
      sendMessage,
      toggleCompare,
      clearCompare,
      saveItem,
      removeSavedItem,
    }),
    [
      userId,
      conversationId,
      messages,
      activity,
      preferences,
      savedItems,
      compareIds,
      isSending,
      chatError,
      sendMessage,
      toggleCompare,
      clearCompare,
      saveItem,
      removeSavedItem,
    ]
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used within AppStateProvider");
  return ctx;
}

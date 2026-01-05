import { api } from "./api.js";

export const state = {
  me: null,
  auth: {
    checked: false,
    error: null,
  },
  conversations: [],
  activeConversationId: null,
  messages: [],
  streaming: false,
};

export function setMe(me) {
  state.me = me;
  state.auth.checked = true;
  state.auth.error = null;
}

export function setAuthError(err) {
  state.me = null;
  state.auth.checked = true;
  state.auth.error = err || null;
}

export async function loadMeOnce() {
  if (state.auth.checked) return;
  try {
    const me = await api.me();
    setMe(me);
  } catch (e) {
    // 401 is normal when not logged in
    setAuthError(e);
  }
}

export function setConversations(convs) {
  state.conversations = convs;
  if (state.activeConversationId && !convs.find(c => c.id === state.activeConversationId)) {
    state.activeConversationId = null;
  }
}

export function setActiveConversation(id) {
  state.activeConversationId = id;
  state.messages = [];
}

export function setMessages(msgs) {
  state.messages = msgs;
}

export function addMessage(msg) {
  state.messages.push(msg);
}

export function updateLastAssistantContent(extraText) {
  const last = state.messages[state.messages.length - 1];
  if (!last || last.role !== "assistant") return;
  last.content += extraText;
}

export function setStreaming(v) {
  state.streaming = v;
}
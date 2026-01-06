(function () {
  const page = document.getElementById("page");
  const logoutBtn = document.getElementById("logoutBtn");
  const meBadge = document.getElementById("meBadge");

  let state = {
    me: null,
    conversations: [],
    activeConversationId: null,
    messages: [],
    streaming: false,
    eventSource: null,
  };

  function setRoute(path) {
    history.pushState({}, "", path);
    render();
  }

  window.addEventListener("popstate", () => render());

  function fmtTime(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleString();
    } catch {
      return iso;
    }
  }

  function el(html) {
    const t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  }

  function showNotice(container, type, text) {
    const n = el(`<div class="notice ${type}">${text}</div>`);
    container.appendChild(n);
    setTimeout(() => {
      try { n.remove(); } catch {}
    }, 7000);
  }

  async function loadMe() {
    try {
      const me = await API.apiFetch("/api/me");
      state.me = me;
      meBadge.textContent = `${me.email} (${me.role})`;
      meBadge.classList.remove("hidden");
      logoutBtn.classList.remove("hidden");
    } catch {
      state.me = null;
      meBadge.classList.add("hidden");
      logoutBtn.classList.add("hidden");
    }
  }

  logoutBtn.addEventListener("click", async () => {
    try {
      await API.apiFetch("/api/auth/logout", { method: "POST" });
    } catch {}
    state = { ...state, me: null, conversations: [], activeConversationId: null, messages: [] };
    setRoute("/login");
  });

  // ---------- Views ----------
  function viewLogin() {
    const root = el(`
      <div class="container">
        <div class="grid2">
          <div class="card">
            <h2>Login</h2>
            <div class="form-row">
              <div class="label">Email</div>
              <input id="email" class="input" type="email" autocomplete="username" />
            </div>
            <div class="form-row">
              <div class="label">Password</div>
              <input id="pw" class="input" type="password" autocomplete="current-password" />
            </div>
            <div class="form-actions">
              <button id="loginBtn" class="btn btn-primary">Login</button>
              <button id="toReg" class="btn btn-secondary">Register</button>
            </div>
            <div class="notice">Login ist nur möglich, wenn dein Account vom Admin <b>approved</b> wurde.</div>
          </div>
          <div class="card">
            <h3>Hinweis</h3>
            <div class="small">
              Dieses Projekt nutzt JWT in <b>httpOnly Cookies</b> + <b>CSRF Schutz</b> (double submit cookie).
              Backend läuft intern auf HTTP, HTTPS kommt über Caddy (tls internal).
            </div>
            <hr class="sep" />
            <div class="small">
              Falls du frisch registriert bist: Admin muss dich im <b>/admin</b> Panel freischalten.
            </div>
          </div>
        </div>
      </div>
    `);

    const email = root.querySelector("#email");
    const pw = root.querySelector("#pw");
    const loginBtn = root.querySelector("#loginBtn");
    const toReg = root.querySelector("#toReg");

    toReg.addEventListener("click", () => setRoute("/register"));

    loginBtn.addEventListener("click", async () => {
      try {
        await API.apiFetch("/api/auth/login", { method: "POST", body: { email: email.value, password: pw.value } });
        await loadMe();
        if (state.me && state.me.role === "admin") setRoute("/admin");
        else setRoute("/");
      } catch (e) {
        showNotice(root, "err", e.message);
      }
    });

    return root;
  }

  function viewRegister() {
    const root = el(`
      <div class="container">
        <div class="card">
          <h2>Register</h2>
          <div class="form-row">
            <div class="label">Email</div>
            <input id="email" class="input" type="email" autocomplete="username" />
          </div>
          <div class="form-row">
            <div class="label">Password (min. 8 Zeichen)</div>
            <input id="pw" class="input" type="password" autocomplete="new-password" />
          </div>
          <div class="form-actions">
            <button id="regBtn" class="btn btn-primary">Register</button>
            <button id="toLogin" class="btn btn-secondary">Back to Login</button>
          </div>
          <div class="notice">
            Registrierung erstellt den User im Status <b>pending</b>. Login erst nach <b>approved</b>.
          </div>
        </div>
      </div>
    `);

    const email = root.querySelector("#email");
    const pw = root.querySelector("#pw");
    const regBtn = root.querySelector("#regBtn");
    const toLogin = root.querySelector("#toLogin");

    toLogin.addEventListener("click", () => setRoute("/login"));

    regBtn.addEventListener("click", async () => {
      try {
        const res = await API.apiFetch("/api/auth/register", { method: "POST", body: { email: email.value, password: pw.value } });
        showNotice(root, "ok", res.message || "Registered.");
      } catch (e) {
        showNotice(root, "err", e.message);
      }
    });

    return root;
  }

  async function refreshConversations() {
    const res = await API.apiFetch("/api/conversations");
    state.conversations = res.conversations || [];
  }

  async function openConversation(id) {
    state.activeConversationId = id;
    const res = await API.apiFetch(`/api/conversations/${id}/messages`);
    state.messages = res.messages || [];
  }

  async function createConversation() {
    const res = await API.apiFetch("/api/conversations", { method: "POST", body: { title: "New Chat" } });
    await refreshConversations();
    await openConversation(res.conversation.id);
  }

  async function renameConversation(id, newTitle) {
    await API.apiFetch(`/api/conversations/${id}`, { method: "PATCH", body: { title: newTitle } });
    await refreshConversations();
  }

  async function deleteConversation(id) {
    await API.apiFetch(`/api/conversations/${id}`, { method: "DELETE" });
    if (state.activeConversationId === id) {
      state.activeConversationId = null;
      state.messages = [];
    }
    await refreshConversations();
  }

  function stopStreaming() {
    try {
      if (state.eventSource) state.eventSource.close();
    } catch {}
    state.streaming = false;
    state.eventSource = null;
  }

  function viewChat() {
    const root = el(`
      <div class="chat-layout">
        <div class="sidebar">
          <div class="sidebar-header">
            <div>
              <div style="font-weight:700">Conversations</div>
              <div class="small">Nur deine eigenen (Admin sieht nur eigene Chats in MVP).</div>
            </div>
            <button id="newConv" class="btn btn-primary">New</button>
          </div>
          <div id="convList" class="sidebar-list"></div>
        </div>

        <div class="chat-panel">
          <div class="chat-header">
            <div>
              <div id="chatTitle" style="font-weight:700">No conversation selected</div>
              <div id="chatMeta" class="small">Erstelle oder wähle eine Konversation.</div>
            </div>
            <div style="display:flex; gap:8px; align-items:center;">
              <button id="stopBtn" class="btn btn-secondary hidden">Stop</button>
              <button id="adminBtn" class="btn btn-secondary hidden">Admin</button>
            </div>
          </div>

          <div id="messages" class="chat-messages"></div>

          <div class="chat-compose">
            <textarea id="input" class="textarea" placeholder="Schreibe eine Nachricht..." ></textarea>
            <button id="sendBtn" class="btn btn-primary">Send</button>
          </div>
        </div>
      </div>
    `);

    const convList = root.querySelector("#convList");
    const newConvBtn = root.querySelector("#newConv");
    const messagesDiv = root.querySelector("#messages");
    const input = root.querySelector("#input");
    const sendBtn = root.querySelector("#sendBtn");
    const chatTitle = root.querySelector("#chatTitle");
    const chatMeta = root.querySelector("#chatMeta");
    const adminBtn = root.querySelector("#adminBtn");
    const stopBtn = root.querySelector("#stopBtn");

    if (state.me && state.me.role === "admin") adminBtn.classList.remove("hidden");
    adminBtn.addEventListener("click", () => setRoute("/admin"));

    stopBtn.addEventListener("click", () => stopStreaming());

    function renderConvList() {
      convList.innerHTML = "";
      if (!state.conversations.length) {
        convList.appendChild(el(`<div class="small" style="padding:10px;">Noch keine Konversationen.</div>`));
        return;
      }
      state.conversations.forEach(c => {
        const item = el(`
          <div class="conv-item ${state.activeConversationId === c.id ? "active" : ""}">
            <div class="conv-title">${escapeHtml(c.title)}</div>
            <div class="conv-actions">
              <button class="icon-btn" title="Rename">✎</button>
              <button class="icon-btn" title="Delete">🗑</button>
            </div>
          </div>
        `);

        const [renameBtn, delBtn] = item.querySelectorAll("button");
        item.addEventListener("click", async (ev) => {
          if (ev.target === renameBtn || ev.target === delBtn) return;
          stopStreaming();
          await openConversation(c.id);
          renderChat();
          renderConvList();
        });

        renameBtn.addEventListener("click", async (ev) => {
          ev.stopPropagation();
          const nt = prompt("Neuer Titel:", c.title);
          if (!nt) return;
          await renameConversation(c.id, nt);
          renderConvList();
          renderChat();
        });

        delBtn.addEventListener("click", async (ev) => {
          ev.stopPropagation();
          if (!confirm("Konversation wirklich löschen?")) return;
          stopStreaming();
          await deleteConversation(c.id);
          renderConvList();
          renderChat();
        });

        convList.appendChild(item);
      });
    }

    function renderMessages() {
      messagesDiv.innerHTML = "";
      if (!state.activeConversationId) {
        messagesDiv.appendChild(el(`<div class="small">Wähle links eine Konversation oder erstelle eine neue.</div>`));
        return;
      }
      state.messages.forEach(m => {
        const box = el(`
          <div class="msg ${m.role}">
            <div class="meta">${m.role.toUpperCase()} • ${fmtTime(m.created_at)}</div>
            <div class="content"></div>
          </div>
        `);
        box.querySelector(".content").textContent = m.content;
        messagesDiv.appendChild(box);
      });
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    function renderChat() {
      const active = state.conversations.find(c => c.id === state.activeConversationId);
      if (!active) {
        chatTitle.textContent = "No conversation selected";
        chatMeta.textContent = "Erstelle oder wähle eine Konversation.";
      } else {
        chatTitle.textContent = active.title;
        chatMeta.textContent = `Updated: ${fmtTime(active.updated_at)}`;
      }
      renderMessages();

      stopBtn.classList.toggle("hidden", !state.streaming);
      sendBtn.disabled = !state.activeConversationId || state.streaming;
      input.disabled = !state.activeConversationId || state.streaming;
    }

    newConvBtn.addEventListener("click", async () => {
      try {
        stopStreaming();
        await createConversation();
        renderConvList();
        renderChat();
      } catch (e) {
        showNotice(root, "err", e.message);
      }
    });

    async function sendMessage() {
      const text = (input.value || "").trim();
      if (!text) return;

      if (!state.activeConversationId) {
        showNotice(root, "err", "Bitte zuerst eine Konversation erstellen.");
        return;
      }

      try {
        // Store user message
        await API.apiFetch(`/api/conversations/${state.activeConversationId}/messages`, {
          method: "POST",
          body: { role: "user", content: text }
        });

        input.value = "";

        // Reload messages to include user msg
        await openConversation(state.activeConversationId);
        renderChat();

        // Stream assistant
        startStream();
      } catch (e) {
        showNotice(root, "err", e.message);
      }
    }

    function startStream() {
      stopStreaming();
      state.streaming = true;
      renderChat();

      // Add a placeholder assistant message in UI immediately
      const placeholder = { id: "tmp_" + Date.now(), role: "assistant", content: "", created_at: new Date().toISOString() };
      state.messages.push(placeholder);
      renderMessages();
      stopBtn.classList.remove("hidden");
      sendBtn.disabled = true;
      input.disabled = true;

      const url = `/api/conversations/${state.activeConversationId}/stream`;
      const es = new EventSource(url, { withCredentials: true });
      state.eventSource = es;

      es.addEventListener("meta", (ev) => {
        // optional
      });

      es.addEventListener("token", (ev) => {
        try {
          const data = JSON.parse(ev.data);
          placeholder.content += data.token || "";
          // update last message content
          const nodes = messagesDiv.querySelectorAll(".msg.assistant .content");
          if (nodes.length) nodes[nodes.length - 1].textContent = placeholder.content;
          messagesDiv.scrollTop = messagesDiv.scrollHeight;
        } catch {}
      });

      es.addEventListener("done", async (ev) => {
        try {
          // reload messages + conv meta
          await refreshConversations();
          await openConversation(state.activeConversationId);
          stopStreaming();
          renderConvList();
          renderChat();
        } catch {
          stopStreaming();
          renderChat();
        }
      });

      es.addEventListener("error", (ev) => {
        stopStreaming();
        renderChat();
        showNotice(root, "err", "Stream error (siehe logs/app.log).");
      });
    }

    sendBtn.addEventListener("click", sendMessage);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Initial render
    renderConvList();
    renderChat();

    // Helpers
    function escapeHtml(s) {
      return (s || "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
      }[c]));
    }

    // Load data async
    (async () => {
      try {
        await refreshConversations();
        // auto-open newest
        if (state.conversations.length && !state.activeConversationId) {
          await openConversation(state.conversations[0].id);
        }
        renderConvList();
        renderChat();
      } catch (e) {
        showNotice(root, "err", e.message);
      }
    })();

    return root;
  }

  function viewAdmin() {
    const root = el(`
      <div class="container">
        <div class="card">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:10px;">
            <div>
              <h2 style="margin:0 0 6px 0;">Admin Panel</h2>
              <div class="small">Approve/Deny pending Users</div>
            </div>
            <div style="display:flex; gap:10px;">
              <button id="backBtn" class="btn btn-secondary">Back to Chat</button>
              <button id="refreshBtn" class="btn btn-primary">Refresh</button>
            </div>
          </div>

          <hr class="sep" />

          <table class="table">
            <thead>
              <tr><th>ID</th><th>Email</th><th>Status</th><th>Created</th><th>Actions</th></tr>
            </thead>
            <tbody id="tbody"></tbody>
          </table>

          <div class="notice">Tipp: Nutzer registrieren sich als <b>pending</b>. Hier freischalten.</div>
        </div>
      </div>
    `);

    const tbody = root.querySelector("#tbody");
    const refreshBtn = root.querySelector("#refreshBtn");
    const backBtn = root.querySelector("#backBtn");

    backBtn.addEventListener("click", () => setRoute("/"));

    async function loadPending() {
      tbody.innerHTML = "";
      try {
        const res = await API.apiFetch("/api/admin/users?status=pending");
        const users = res.users || [];
        if (!users.length) {
          tbody.appendChild(el(`<tr><td colspan="5" class="small">Keine pending Users.</td></tr>`));
          return;
        }
        users.forEach(u => {
          const tr = el(`
            <tr>
              <td>${u.id}</td>
              <td>${escapeHtml(u.email)}</td>
              <td>${escapeHtml(u.status)}</td>
              <td>${escapeHtml(u.created_at)}</td>
              <td style="display:flex; gap:8px; padding-top:8px; padding-bottom:8px;">
                <button class="btn btn-primary">Approve</button>
                <button class="btn btn-danger">Deny</button>
              </td>
            </tr>
          `);
          const [approveBtn, denyBtn] = tr.querySelectorAll("button");

          approveBtn.addEventListener("click", async () => {
            try {
              await API.apiFetch(`/api/admin/users/${u.id}/approve`, { method: "POST" });
              await loadPending();
            } catch (e) {
              showNotice(root, "err", e.message);
            }
          });

          denyBtn.addEventListener("click", async () => {
            try {
              await API.apiFetch(`/api/admin/users/${u.id}/deny`, { method: "POST" });
              await loadPending();
            } catch (e) {
              showNotice(root, "err", e.message);
            }
          });

          tbody.appendChild(tr);
        });
      } catch (e) {
        showNotice(root, "err", e.message);
      }
    }

    refreshBtn.addEventListener("click", loadPending);
    loadPending();

    function escapeHtml(s) {
      return (s || "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
      }[c]));
    }

    return root;
  }

  // ---------- Router ----------
  async function guard() {
    await loadMe();
    const path = location.pathname;

    const publicRoutes = ["/login", "/register"];
    if (!state.me && !publicRoutes.includes(path)) {
      setRoute("/login");
      return false;
    }
    if (state.me && publicRoutes.includes(path)) {
      setRoute("/");
      return false;
    }
    if (path === "/admin" && state.me && state.me.role !== "admin") {
      setRoute("/");
      return false;
    }
    return true;
  }

  async function render() {
    const ok = await guard();
    if (!ok) return;

    const path = location.pathname;

    page.innerHTML = "";
    if (path === "/login") page.appendChild(viewLogin());
    else if (path === "/register") page.appendChild(viewRegister());
    else if (path === "/admin") page.appendChild(viewAdmin());
    else page.appendChild(viewChat());
  }

  // Initial
  render();
})();
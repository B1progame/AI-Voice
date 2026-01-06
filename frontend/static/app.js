(function () {
  const page = document.getElementById("page");

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

  function el(html) {
    const t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  }

  // API Wrapper (bleibt gleich wie vorher, gekürzt für Übersicht)
  async function loadMe() {
    try {
      state.me = await API.apiFetch("/api/me");
    } catch {
      state.me = null;
    }
  }

  async function doLogout() {
    try { await API.apiFetch("/api/auth/logout", { method: "POST" }); } catch {}
    state.me = null;
    setRoute("/login");
  }

  // --- Views ---

  function viewLogin() {
    const root = el(`
      <div class="center-view">
        <div class="card">
          <h2 style="margin-top:0; color:#fff;">Login</h2>
          <div class="form-row">
            <label class="label">Email</label>
            <input id="email" class="input" type="email">
          </div>
          <div class="form-row">
            <label class="label">Password</label>
            <input id="pw" class="input" type="password">
          </div>
          <div class="form-actions">
            <button id="toReg" class="btn btn-secondary">Register</button>
            <button id="loginBtn" class="btn btn-primary">Sign In</button>
          </div>
          <div id="noticeArea" style="margin-top:15px;"></div>
        </div>
      </div>
    `);
    
    const email = root.querySelector("#email");
    const pw = root.querySelector("#pw");
    
    root.querySelector("#loginBtn").addEventListener("click", async () => {
      try {
        await API.apiFetch("/api/auth/login", { method: "POST", body: { email: email.value, password: pw.value } });
        await loadMe();
        setRoute("/");
      } catch(e) {
        root.querySelector("#noticeArea").innerHTML = `<div class="notice err">${e.message}</div>`;
      }
    });
    root.querySelector("#toReg").addEventListener("click", () => setRoute("/register"));
    return root;
  }

  function viewRegister() {
    const root = el(`
      <div class="center-view">
        <div class="card">
          <h2 style="margin-top:0; color:#fff;">Register</h2>
          <div class="form-row">
            <label class="label">Email</label>
            <input id="email" class="input" type="email">
          </div>
          <div class="form-row">
            <label class="label">Password</label>
            <input id="pw" class="input" type="password">
          </div>
          <div class="form-actions">
            <button id="toLogin" class="btn btn-secondary">Back</button>
            <button id="regBtn" class="btn btn-primary">Create Account</button>
          </div>
          <div id="noticeArea" style="margin-top:15px;"></div>
        </div>
      </div>
    `);
    
    const email = root.querySelector("#email");
    const pw = root.querySelector("#pw");

    root.querySelector("#regBtn").addEventListener("click", async () => {
      try {
        const res = await API.apiFetch("/api/auth/register", { method: "POST", body: { email: email.value, password: pw.value } });
        root.querySelector("#noticeArea").innerHTML = `<div class="notice ok">${res.message || "Account created."}</div>`;
      } catch(e) {
        root.querySelector("#noticeArea").innerHTML = `<div class="notice err">${e.message}</div>`;
      }
    });
    root.querySelector("#toLogin").addEventListener("click", () => setRoute("/login"));
    return root;
  }

  function viewChat() {
    // Hier ist das Layout: Sidebar links, Header oben rechts integriert
    const root = el(`
      <div class="chat-layout">
        <div id="sidebar" class="sidebar">
          <div class="sidebar-header">
            <div class="sidebar-title">Chats</div>
            <button id="newConv" class="btn btn-primary" style="padding:4px 10px;">+</button>
          </div>
          <div id="convList" class="sidebar-list"></div>
        </div>
        
        <div id="sidebarOverlay" class="sidebar-overlay"></div>

        <div class="chat-panel">
          <div class="chat-header">
            <div style="display:flex; align-items:center;">
              <button id="mobileMenu" class="mobile-menu-btn">☰</button>
              <div id="chatTitle" style="font-weight:700;">AI Assistant</div>
            </div>
            
            <div style="display:flex; align-items:center; gap:10px;">
              <span class="badge">${state.me ? state.me.email : ''}</span>
              <button id="adminBtn" class="btn btn-secondary hidden">Admin</button>
              <button id="logoutBtn" class="btn btn-secondary" style="font-size:0.8rem;">Logout</button>
            </div>
          </div>

          <div id="messages" class="chat-messages">
             </div>

          <div class="chat-compose">
            <textarea id="input" class="textarea" rows="1" placeholder="Nachricht an AI..."></textarea>
            <button id="sendBtn" class="btn btn-primary" style="border-radius:50%; width:44px; height:44px;">➤</button>
            <button id="stopBtn" class="btn btn-danger hidden" style="border-radius:50%; width:44px; height:44px;">■</button>
          </div>
        </div>
      </div>
    `);

    // Logic Refs
    const sidebar = root.querySelector("#sidebar");
    const overlay = root.querySelector("#sidebarOverlay");
    const convList = root.querySelector("#convList");
    const msgContainer = root.querySelector("#messages");
    const input = root.querySelector("#input");
    const sendBtn = root.querySelector("#sendBtn");
    const stopBtn = root.querySelector("#stopBtn");
    const adminBtn = root.querySelector("#adminBtn");

    // Admin Button check
    if (state.me && state.me.role === "admin") {
      adminBtn.classList.remove("hidden");
      adminBtn.addEventListener("click", () => setRoute("/admin"));
    }

    // Logout
    root.querySelector("#logoutBtn").addEventListener("click", doLogout);
    
    // Mobile Sidebar
    root.querySelector("#mobileMenu").addEventListener("click", () => sidebar.classList.add("open"));
    overlay.addEventListener("click", () => sidebar.classList.remove("open"));

    // --- Chat Logic Copies (Data Fetching etc) ---
    async function renderConvs() {
      convList.innerHTML = "";
      try {
        const res = await API.apiFetch("/api/conversations");
        state.conversations = res.conversations || [];
        
        if (!state.conversations.length) {
            convList.innerHTML = `<div style="padding:10px; font-size:0.8rem; color:#8b949e; text-align:center;">Keine Chats</div>`;
        }

        state.conversations.forEach(c => {
          const item = el(`
            <div class="conv-item ${state.activeConversationId === c.id ? 'active' : ''}">
              <div class="conv-title">${c.title || 'New Chat'}</div>
              <button class="btn-icon del">×</button>
            </div>
          `);
          item.addEventListener("click", (e) => {
             if(e.target.closest('.del')) return;
             loadConv(c.id);
             sidebar.classList.remove("open");
          });
          item.querySelector(".del").addEventListener("click", async () => {
             if(confirm("Löschen?")) {
                 await API.apiFetch(`/api/conversations/${c.id}`, { method: "DELETE" });
                 if(state.activeConversationId == c.id) { state.activeConversationId = null; state.messages = []; renderMessages(); }
                 renderConvs();
             }
          });
          convList.appendChild(item);
        });
      } catch {}
    }

    async function renderMessages() {
      msgContainer.innerHTML = "";
      if(!state.activeConversationId) {
        msgContainer.innerHTML = `<div style="text-align:center; color:#8b949e; margin-top:50px;">Wähle oder starte einen Chat.</div>`;
        return;
      }
      state.messages.forEach(m => {
        const bubble = el(`
           <div class="msg ${m.role}">
             <div class="content"></div>
           </div>
        `);
        bubble.querySelector(".content").textContent = m.content;
        msgContainer.appendChild(bubble);
      });
      msgContainer.scrollTop = msgContainer.scrollHeight;
    }

    async function loadConv(id) {
        state.activeConversationId = id;
        const res = await API.apiFetch(`/api/conversations/${id}/messages`);
        state.messages = res.messages;
        renderConvs(); // update active class
        renderMessages();
    }

    root.querySelector("#newConv").addEventListener("click", async () => {
        const res = await API.apiFetch("/api/conversations", { method: "POST", body: { title: "New Chat" }});
        loadConv(res.conversation.id);
    });

    // Sending
    async function send() {
        const txt = input.value.trim();
        if(!txt || !state.activeConversationId) return;
        
        // Optimistic UI
        state.messages.push({ role: 'user', content: txt });
        renderMessages();
        input.value = "";

        await API.apiFetch(`/api/conversations/${state.activeConversationId}/messages`, {
            method: "POST", body: { role: 'user', content: txt }
        });

        // Streaming start
        state.streaming = true;
        sendBtn.classList.add("hidden");
        stopBtn.classList.remove("hidden");
        
        const placeholder = { role: 'assistant', content: "..." };
        state.messages.push(placeholder);
        renderMessages();

        const es = new EventSource(`/api/conversations/${state.activeConversationId}/stream`, { withCredentials: true });
        state.eventSource = es;
        let fullText = "";

        es.addEventListener("token", (e) => {
            const d = JSON.parse(e.data);
            fullText += d.token;
            // Update last message in DOM directly for smooth stream
            const bubbles = msgContainer.querySelectorAll(".msg.assistant .content");
            if(bubbles.length) bubbles[bubbles.length-1].textContent = fullText;
            msgContainer.scrollTop = msgContainer.scrollHeight;
        });

        const finish = async () => {
             es.close();
             state.streaming = false;
             stopBtn.classList.add("hidden");
             sendBtn.classList.remove("hidden");
             await loadConv(state.activeConversationId); // reload clean
        };
        es.addEventListener("done", finish);
        es.addEventListener("error", finish);
        
        stopBtn.onclick = () => { finish(); };
    }

    sendBtn.addEventListener("click", send);
    input.addEventListener("keydown", e => { if(e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }});

    // Init
    renderConvs();
    if(state.activeConversationId) loadConv(state.activeConversationId);
    
    return root;
  }

  function viewAdmin() {
    const root = el(`
      <div class="container" style="max-width:800px; margin:40px auto; padding:20px;">
        <div class="card">
          <div style="display:flex; justify-content:space-between; margin-bottom:20px;">
             <h2>Admin Panel</h2>
             <button id="backBtn" class="btn btn-secondary">Back to Chat</button>
          </div>
          <table style="width:100%; text-align:left;">
            <thead><tr><th>Email</th><th>Status</th><th>Action</th></tr></thead>
            <tbody id="tbody"></tbody>
          </table>
        </div>
      </div>
    `);
    
    root.querySelector("#backBtn").addEventListener("click", () => setRoute("/"));
    
    (async () => {
       const res = await API.apiFetch("/api/admin/users?status=pending");
       const tbody = root.querySelector("#tbody");
       if(!res.users.length) tbody.innerHTML = "<tr><td colspan='3'>No pending users.</td></tr>";
       res.users.forEach(u => {
           const tr = el(`
             <tr>
               <td>${u.email}</td>
               <td>${u.status}</td>
               <td>
                 <button class="btn btn-primary ok">Approve</button>
                 <button class="btn btn-danger no">Deny</button>
               </td>
             </tr>
           `);
           tr.querySelector(".ok").onclick = async () => {
               await API.apiFetch(`/api/admin/users/${u.id}/approve`, { method: "POST"});
               setRoute("/admin"); // reload
           };
           tr.querySelector(".no").onclick = async () => {
               await API.apiFetch(`/api/admin/users/${u.id}/deny`, { method: "POST"});
               setRoute("/admin");
           };
           tbody.appendChild(tr);
       });
    })();

    return root;
  }

  // --- Router ---
  async function render() {
    const path = location.pathname;
    page.innerHTML = "";
    
    // Auth Check
    if(!state.me && !["/login", "/register"].includes(path)) {
        await loadMe();
        if(!state.me) return setRoute("/login");
    }

    if(path === "/login") page.appendChild(viewLogin());
    else if(path === "/register") page.appendChild(viewRegister());
    else if(path === "/admin") page.appendChild(viewAdmin());
    else page.appendChild(viewChat());
  }

  render();
})();
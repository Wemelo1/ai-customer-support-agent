/**
 * SupportAI Web Widget
 * 
 * Embed on ANY website with just one line:
 * <script src="https://your-api-url.com/widget.js" data-business="My Business"></script>
 */
(function () {
  const API_URL = document.currentScript?.getAttribute("data-api") || "http://localhost:8000";
  const BUSINESS = document.currentScript?.getAttribute("data-business") || "Support";
  const PRIMARY = document.currentScript?.getAttribute("data-color") || "#2563eb";

  let sessionId = "web-" + Math.random().toString(36).slice(2);
  let isOpen = false;
  let messageHistory = [];

  // ── Inject styles ────────────────────────────────────────────────────────
  const style = document.createElement("style");
  style.textContent = `
    #supportai-widget * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    #supportai-bubble { position: fixed; bottom: 24px; right: 24px; width: 56px; height: 56px;
      background: ${PRIMARY}; border-radius: 50%; display: flex; align-items: center; justify-content: center;
      cursor: pointer; box-shadow: 0 4px 16px rgba(0,0,0,0.2); z-index: 9999; border: none; transition: transform 0.2s; }
    #supportai-bubble:hover { transform: scale(1.08); }
    #supportai-bubble svg { width: 26px; height: 26px; fill: white; }
    #supportai-panel { position: fixed; bottom: 92px; right: 24px; width: 360px; height: 520px;
      background: white; border-radius: 16px; box-shadow: 0 8px 40px rgba(0,0,0,0.18);
      display: flex; flex-direction: column; z-index: 9998; overflow: hidden;
      transform: scale(0.9) translateY(20px); opacity: 0; pointer-events: none;
      transition: all 0.25s cubic-bezier(0.4,0,0.2,1); }
    #supportai-panel.open { transform: scale(1) translateY(0); opacity: 1; pointer-events: all; }
    #supportai-header { background: ${PRIMARY}; padding: 16px; color: white; display: flex; align-items: center; gap: 10px; }
    #supportai-header .av { width: 36px; height: 36px; border-radius: 50%; background: rgba(255,255,255,0.25);
      display: flex; align-items: center; justify-content: center; font-size: 18px; }
    #supportai-header h3 { margin: 0; font-size: 15px; font-weight: 600; }
    #supportai-header p { margin: 0; font-size: 12px; opacity: 0.85; }
    #supportai-header .close-btn { margin-left: auto; background: none; border: none; color: white;
      cursor: pointer; font-size: 20px; padding: 0; line-height: 1; opacity: 0.8; }
    #supportai-header .close-btn:hover { opacity: 1; }
    #supportai-messages { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; background: #f8f9fa; }
    .sai-msg { max-width: 80%; padding: 9px 12px; border-radius: 12px; font-size: 14px; line-height: 1.5; word-wrap: break-word; }
    .sai-bot { background: white; border: 1px solid #e5e7eb; color: #111; align-self: flex-start; border-radius: 4px 12px 12px 12px; }
    .sai-user { background: ${PRIMARY}; color: white; align-self: flex-end; border-radius: 12px 4px 12px 12px; }
    .sai-badge { font-size: 11px; padding: 2px 7px; border-radius: 10px; display: inline-block; margin-top: 5px; }
    .sai-badge-ticket { background: #dcfce7; color: #15803d; }
    .sai-badge-escalate { background: #fee2e2; color: #dc2626; }
    .sai-typing { display: flex; gap: 4px; padding: 4px 0; align-items: center; }
    .sai-typing span { width: 7px; height: 7px; border-radius: 50%; background: #9ca3af; animation: sai-blink 1.2s infinite; }
    .sai-typing span:nth-child(2) { animation-delay: 0.2s; }
    .sai-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes sai-blink { 0%,80%,100%{opacity:0.2} 40%{opacity:1} }
    .sai-quick-btns { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }
    .sai-quick-btn { font-size: 12px; padding: 4px 10px; border: 1px solid #e5e7eb; border-radius: 20px;
      background: white; cursor: pointer; color: #374151; transition: all 0.15s; }
    .sai-quick-btn:hover { background: ${PRIMARY}; color: white; border-color: ${PRIMARY}; }
    #supportai-input-row { padding: 10px; display: flex; gap: 8px; border-top: 1px solid #f3f4f6; background: white; }
    #supportai-input { flex: 1; border: 1px solid #e5e7eb; border-radius: 20px; padding: 8px 14px;
      font-size: 14px; outline: none; }
    #supportai-input:focus { border-color: ${PRIMARY}; }
    #supportai-send { width: 36px; height: 36px; border-radius: 50%; background: ${PRIMARY};
      border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
    #supportai-send svg { width: 16px; height: 16px; fill: white; }
    #supportai-send:hover { opacity: 0.85; }
    #supportai-notif { position: absolute; top: -4px; right: -4px; width: 18px; height: 18px;
      background: #ef4444; border-radius: 50%; color: white; font-size: 11px; font-weight: 600;
      display: none; align-items: center; justify-content: center; }
  `;
  document.head.appendChild(style);

  // ── Build HTML ───────────────────────────────────────────────────────────
  const widget = document.createElement("div");
  widget.id = "supportai-widget";
  widget.innerHTML = `
    <button id="supportai-bubble" aria-label="Open support chat">
      <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>
      <span id="supportai-notif">1</span>
    </button>
    <div id="supportai-panel" role="dialog" aria-label="Support chat">
      <div id="supportai-header">
        <div class="av">🤖</div>
        <div><h3>${BUSINESS} Support</h3><p>🟢 Online · AI-powered</p></div>
        <button class="close-btn" id="supportai-close" aria-label="Close chat">✕</button>
      </div>
      <div id="supportai-messages"></div>
      <div id="supportai-input-row">
        <input id="supportai-input" type="text" placeholder="Type your message..." autocomplete="off">
        <button id="supportai-send" aria-label="Send">
          <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
      </div>
    </div>
  `;
  document.body.appendChild(widget);

  // ── Logic ────────────────────────────────────────────────────────────────
  const bubble = document.getElementById("supportai-bubble");
  const panel = document.getElementById("supportai-panel");
  const closeBtn = document.getElementById("supportai-close");
  const input = document.getElementById("supportai-input");
  const sendBtn = document.getElementById("supportai-send");
  const messages = document.getElementById("supportai-messages");
  const notif = document.getElementById("supportai-notif");

  function toggleWidget() {
    isOpen = !isOpen;
    panel.classList.toggle("open", isOpen);
    notif.style.display = "none";
    if (isOpen && messageHistory.length === 0) sendGreeting();
    if (isOpen) setTimeout(() => input.focus(), 300);
  }

  function addMessage(text, role, extra) {
    const div = document.createElement("div");
    div.className = `sai-msg sai-${role}`;
    div.innerHTML = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
    if (extra?.ticket) div.innerHTML += `<br><span class="sai-badge sai-badge-ticket">🎫 ${extra.ticket}</span>`;
    if (extra?.escalate) div.innerHTML += `<br><span class="sai-badge sai-badge-escalate">👤 Escalating</span>`;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function showTyping() {
    const div = document.createElement("div");
    div.className = "sai-msg sai-bot"; div.id = "sai-typing";
    div.innerHTML = `<div class="sai-typing"><span></span><span></span><span></span></div>`;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function removeTyping() { document.getElementById("sai-typing")?.remove(); }

  function sendGreeting() {
    const greeting = `👋 Hi! I'm ${BUSINESS}'s AI support agent.\n\nHow can I help you today?`;
    addMessage(greeting, "bot");
    const quickDiv = document.createElement("div");
    quickDiv.className = "sai-quick-btns";
    ["Reset password", "Track order", "Request refund", "Talk to human"].forEach(q => {
      const btn = document.createElement("button");
      btn.className = "sai-quick-btn"; btn.textContent = q;
      btn.onclick = () => send(q);
      quickDiv.appendChild(btn);
    });
    messages.appendChild(quickDiv);
  }

  async function send(text) {
    const msg = text || input.value.trim();
    if (!msg) return;
    input.value = "";
    addMessage(msg, "user");
    showTyping();

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: msg })
      });
      const data = await res.json();
      removeTyping();
      addMessage(data.response, "bot", {
        ticket: data.ticket_id ? `Ticket ${data.ticket_id}` : null,
        escalate: data.escalate
      });
    } catch {
      removeTyping();
      addMessage("Sorry, I'm having connection issues. Please try again.", "bot");
    }
  }

  bubble.addEventListener("click", toggleWidget);
  closeBtn.addEventListener("click", toggleWidget);
  sendBtn.addEventListener("click", () => send());
  input.addEventListener("keydown", e => { if (e.key === "Enter") send(); });

  // Show notification dot after 3 seconds if widget not opened
  setTimeout(() => {
    if (!isOpen) {
      notif.style.display = "flex";
    }
  }, 3000);

})();

/**
 * Wakkii Chat Widget — Embeddable
 * 
 * Drop this script into any HTML page and it auto-creates a chat UI
 * at the bottom of the screen, connects to the Wakkii Chat server,
 * and greets the user.
 * 
 * Usage:
 *   <script src="wakkii-widget.js" 
 *           data-api="http://localhost:8085" 
 *           data-room="AGENT"
 *           data-user="Justin"></script>
 * 
 * Or initialize manually:
 *   WakkiiWidget.init({ api: 'http://localhost:8085', room: 'AGENT', user: 'Justin' });
 */
(function() {
  if (window.WakkiiWidget) return; // Already loaded — don't create duplicate

  const script = document.currentScript || document.querySelector('script[src*="wakkii-widget"]');
  const config = {
    api: script?.dataset?.api || window.WAKKII_API || 'http://localhost:8085',
    room: script?.dataset?.room || window.WAKKII_ROOM || 'CLINE',
    user: script?.dataset?.user || window.WAKKII_USER || 'User',
  };

  let lastCount = 0;
  let userScrolled = false;
  let isTyping = false;
  let isOpen = false;

  // Create styles
  const style = document.createElement('style');
  style.textContent = `
    .wakkii-widget * { margin: 0; padding: 0; box-sizing: border-box; }
    .wakkii-widget {
      position: fixed; bottom: 0; right: 0; z-index: 99999;
      font-family: 'Segoe UI', -apple-system, sans-serif;
    }
    .wakkii-toggle {
      position: fixed; bottom: 20px; right: 20px;
      width: 60px; height: 60px; border-radius: 50%;
      background: linear-gradient(135deg, #E91E63, #9C27B0);
      border: none; cursor: pointer; color: white;
      font-size: 28px; box-shadow: 0 4px 20px rgba(233,30,99,0.4);
      transition: transform 0.3s, box-shadow 0.3s;
      z-index: 99999;
    }
    .wakkii-toggle:hover { transform: scale(1.1); box-shadow: 0 6px 30px rgba(233,30,99,0.6); }
    .wakkii-panel {
      position: fixed; bottom: 90px; right: 20px;
      width: 380px; height: 520px; max-height: 70vh;
      background: #0a0a0f; border-radius: 20px;
      border: 1px solid #9C27B0;
      display: none; flex-direction: column;
      overflow: hidden;
      box-shadow: 0 8px 40px rgba(0,0,0,0.5);
      animation: wakkiiSlideUp 0.3s ease;
    }
    @keyframes wakkiiSlideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    .wakkii-panel.open { display: flex; }
    .wakkii-header {
      background: linear-gradient(135deg, #E91E63, #9C27B0);
      padding: 14px 16px; display: flex; align-items: center; gap: 10px;
    }
    .wakkii-header .logo { width: 36px; height: 36px; border-radius: 50%; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; font-size: 18px; }
    .wakkii-header h2 { font-size: 15px; color: white; font-weight: 600; }
    .wakkii-header .sub { font-size: 11px; color: rgba(255,255,255,0.8); }
    .wakkii-header .devin { margin-left: auto; font-size: 10px; background: rgba(255,255,255,0.15); padding: 3px 8px; border-radius: 10px; color: white; }
    .wakkii-header .devin.on { background: rgba(0,230,118,0.2); color: #00e676; }
    .wakkii-msgs {
      flex: 1; overflow-y: auto; padding: 14px;
      display: flex; flex-direction: column; gap: 8px;
    }
    .wakkii-msgs::-webkit-scrollbar { width: 5px; }
    .wakkii-msgs::-webkit-scrollbar-track { background: #1a1a2e; }
    .wakkii-msgs::-webkit-scrollbar-thumb { background: #E91E63; border-radius: 3px; }
    .wakkii-msg {
      max-width: 80%; padding: 10px 14px; border-radius: 16px;
      font-size: 13px; line-height: 1.4; word-wrap: break-word;
      animation: wakkiiFade 0.3s ease;
    }
    @keyframes wakkiiFade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    .wakkii-msg.user { align-self: flex-end; background: #2196F3; color: white; border-bottom-right-radius: 4px; }
    .wakkii-msg.agent { align-self: flex-start; background: #1a1a2e; border: 1px solid #00e676; color: #00e676; border-bottom-left-radius: 4px; }
    .wakkii-msg.system { align-self: center; background: transparent; color: #8888aa; font-size: 11px; text-align: center; }
    .wakkii-msg .sender { font-size: 9px; opacity: 0.7; margin-bottom: 2px; }
    .wakkii-msg .time { font-size: 8px; opacity: 0.5; margin-top: 3px; }
    .wakkii-typing { align-self: flex-start; color: #8888aa; font-size: 11px; padding: 6px 14px; display: none; }
    .wakkii-typing.on { display: block; }
    .wakkii-input { display: flex; padding: 10px; gap: 8px; background: #1a1a2e; }
    .wakkii-input input {
      flex: 1; background: #0a0a0f; border: 1px solid #9C27B0; color: white;
      padding: 10px 14px; border-radius: 20px; font-size: 13px; outline: none;
    }
    .wakkii-input input:focus { border-color: #E91E63; }
    .wakkii-input button {
      background: linear-gradient(135deg, #E91E63, #9C27B0); color: white;
      border: none; padding: 10px 18px; border-radius: 20px; cursor: pointer;
      font-size: 13px; font-weight: 600; transition: transform 0.2s;
    }
    .wakkii-input button:hover { transform: scale(1.05); }
  `;
  document.head.appendChild(style);

  // Create toggle button
  const toggle = document.createElement('button');
  toggle.className = 'wakkii-toggle';
  toggle.innerHTML = '💬';
  toggle.onclick = () => { isOpen = !isOpen; panel.classList.toggle('open', isOpen); };
  document.body.appendChild(toggle);

  // Create panel
  const panel = document.createElement('div');
  panel.className = 'wakkii-panel';
  panel.innerHTML = `
    <div class="wakkii-header">
      <div class="logo">🤖</div>
      <div>
        <h2>Wakkii Agent</h2>
        <div class="sub" id="wakkii-status">Connecting...</div>
      </div>
      <div class="devin" id="wakkii-devin"> Devin</div>
    </div>
    <div class="wakkii-msgs" id="wakkii-msgs">
      <div class="wakkii-msg system">Connecting to Wakkii Chat...</div>
    </div>
    <div class="wakkii-typing" id="wakkii-typing">● ● ● Agent is working</div>
    <div class="wakkii-input">
      <input type="text" id="wakkii-input-field" placeholder="Type a message..." />
      <button id="wakkii-send-btn">Send</button>
    </div>
  `;
  document.body.appendChild(panel);

  const msgsEl = panel.querySelector('#wakkii-msgs');
  const inputEl = panel.querySelector('#wakkii-input-field');
  const sendBtn = panel.querySelector('#wakkii-send-btn');
  const typingEl = panel.querySelector('#wakkii-typing');
  const statusEl = panel.querySelector('#wakkii-status');
  const devinEl = panel.querySelector('#wakkii-devin');

  msgsEl.addEventListener('scroll', () => {
    const dist = msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight;
    userScrolled = dist > 80;
  });

  function scrollToBottom() {
    if (!userScrolled) msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function esc(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
  }

  function addMsg(sender, text, ts) {
    const isAgent = sender === 'Wakkii Agent' || sender.includes('Agent');
    const cls = isAgent ? 'agent' : (sender === 'system' ? 'system' : 'user');
    const div = document.createElement('div');
    div.className = `wakkii-msg ${cls}`;
    const time = ts ? new Date(ts).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '';
    div.innerHTML = `<div class="sender">${sender}</div>${esc(text)}<div class="time">${time}</div>`;
    msgsEl.appendChild(div);
    scrollToBottom();
  }

  async function fetchMsgs() {
    try {
      const resp = await fetch(`${config.api}/wakkii/rooms/${config.room}/messages`);
      const data = await resp.json();
      const msgs = data.messages || [];
      if (msgs.length > lastCount) {
        const newMsgs = msgs.slice(lastCount);
        lastCount = msgs.length;
        for (const msg of newMsgs) {
          addMsg(msg.sender, msg.text, msg.timestamp);
          if (msg.sender.includes('Agent')) {
            isTyping = false;
            typingEl.classList.remove('on');
          }
        }
      } else if (lastCount === 0 && msgs.length > 0) {
        lastCount = msgs.length;
      }
    } catch (e) {
      statusEl.textContent = 'Disconnected';
      statusEl.style.color = '#f44336';
    }
  }

  async function send() {
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = '';
    userScrolled = false;
    addMsg(config.user, text, new Date().toISOString());
    isTyping = true;
    typingEl.classList.add('on');
    try {
      await fetch(`${config.api}/wakkii/rooms/${config.room}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender: config.user, text, timestamp: new Date().toISOString() })
      });
    } catch (e) {
      addMsg('system', 'Failed to send — is the server running?', null);
      isTyping = false;
      typingEl.classList.remove('on');
    }
  }

  async function checkConn() {
    try {
      const resp = await fetch(`${config.api}/health`);
      if (resp.ok) {
        statusEl.textContent = 'Online';
        statusEl.style.color = '#00e676';
        try {
          const dr = await fetch(`${config.api}/devin/status`);
          if (dr.ok) {
            const dd = await dr.json();
            if (dd.connected) {
              devinEl.classList.add('on');
              devinEl.textContent = '✓ Devin';
            }
          }
        } catch (e) {}
      }
    } catch (e) {
      statusEl.textContent = 'Offline';
      statusEl.style.color = '#f44336';
    }
  }

  inputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
  sendBtn.onclick = send;

  // Initialize
  checkConn();
  fetchMsgs();
  setInterval(fetchMsgs, 3000);
  setInterval(checkConn, 30000);

  // Auto-open and greet on first load
  setTimeout(() => {
    isOpen = true;
    panel.classList.add('open');
  }, 1000);

  // Expose API
  window.WakkiiWidget = {
    init: (opts) => { Object.assign(config, opts); },
    open: () => { isOpen = true; panel.classList.add('open'); },
    close: () => { isOpen = false; panel.classList.remove('open'); },
    send: (text) => { inputEl.value = text; send(); },
  };
})();

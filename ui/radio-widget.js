/**
 * Wakkii Radio Widget — V-103 Atlanta floating player
 * 
 * Auto-creates a floating radio widget at bottom-left of the page.
 * Plays V-103 Atlanta stream, shows now-playing song, saves to playlist.
 * Separate from chat widget (which is bottom-right).
 * 
 * Usage:
 *   <script src="radio-widget.js"></script>
 * 
 * Or check if already loaded:
 *   if (!window.WakkiiRadio) { /* load it */ }
 */
(function() {
  if (window.WakkiiRadio) return; // Already loaded — don't create duplicate

  const V103_URL = 'https://live.amperwave.net/direct/audacy-wveefmaac-imc';
  const PLAYLIST_KEY = 'wakkii-radio-playlist';
  const CT_OFFSET_SUMMER = 5; // CDT = UTC-5
  const CT_OFFSET_WINTER = 6; // CST = UTC-6

  let isPlaying = false;
  let audio = null;
  let currentSong = '';
  let showPlaylist = false;
  let playlist = JSON.parse(localStorage.getItem(PLAYLIST_KEY) || '[]');

  // Create styles
  const style = document.createElement('style');
  style.textContent = `
    .wakkii-radio * { margin: 0; padding: 0; box-sizing: border-box; }
    .wakkii-radio {
      position: fixed; bottom: 20px; left: 20px; z-index: 99998;
      width: 320px; background: #0a0a0f; border-radius: 16px;
      border: 1px solid #E91E63; overflow: hidden;
      font-family: 'Segoe UI', -apple-system, sans-serif;
      box-shadow: 0 4px 20px rgba(233,30,99,0.3);
      transition: height 0.3s ease;
    }
    .wakkii-radio-header {
      background: linear-gradient(135deg, #E91E63, #9C27B0);
      padding: 10px 14px; display: flex; align-items: center; gap: 8px;
      cursor: move;
    }
    .wakkii-radio-header .logo { font-size: 20px; }
    .wakkii-radio-header h3 { font-size: 14px; color: white; font-weight: 600; }
    .wakkii-radio-header .sub { font-size: 10px; color: rgba(255,255,255,0.8); }
    .wakkii-radio-header .close {
      margin-left: auto; cursor: pointer; color: rgba(255,255,255,0.7);
      font-size: 16px; padding: 2px 6px;
    }
    .wakkii-radio-header .close:hover { color: white; }
    .wakkii-radio-body { padding: 12px; }
    .wakkii-radio-status {
      font-size: 11px; color: #8888aa; text-align: center; margin-bottom: 8px;
    }
    .wakkii-radio-status.live { color: #00e676; }
    .wakkii-radio-eq {
      display: flex; justify-content: center; gap: 3px; margin: 8px 0;
    }
    .wakkii-radio-eq .bar {
      width: 4px; height: 20px; background: #9C27B0; border-radius: 2px;
      animation: eqBounce 0.8s infinite ease-in-out;
    }
    .wakkii-radio-eq .bar:nth-child(2) { animation-delay: 0.1s; }
    .wakkii-radio-eq .bar:nth-child(3) { animation-delay: 0.2s; }
    .wakkii-radio-eq .bar:nth-child(4) { animation-delay: 0.3s; }
    .wakkii-radio-eq .bar:nth-child(5) { animation-delay: 0.4s; }
    .wakkii-radio-eq .bar:nth-child(6) { animation-delay: 0.5s; }
    .wakkii-radio-eq .bar:nth-child(7) { animation-delay: 0.6s; }
    .wakkii-radio-eq.paused .bar { animation-play-state: paused; opacity: 0.3; }
    @keyframes eqBounce {
      0%, 100% { height: 8px; }
      50% { height: 24px; }
    }
    .wakkii-radio-nowplaying {
      font-size: 9px; color: #8888aa; text-align: center; margin-top: 4px;
    }
    .wakkii-radio-song {
      font-size: 13px; font-weight: 600; color: white; text-align: center;
      margin: 6px 0; padding: 0 10px; word-wrap: break-word;
    }
    .wakkii-radio-save {
      display: block; margin: 8px auto; padding: 6px 14px;
      background: #1a1a2e; border: 1px solid #9C27B0; border-radius: 12px;
      color: white; font-size: 11px; cursor: pointer; transition: all 0.2s;
    }
    .wakkii-radio-save:hover { background: #9C27B0; }
    .wakkii-radio-save.saved { background: #FFD700; color: #0a0a0f; border-color: #FFD700; }
    .wakkii-radio-controls {
      display: flex; justify-content: center; gap: 12px; margin-top: 8px;
    }
    .wakkii-radio-btn {
      width: 44px; height: 44px; border-radius: 50%; border: none;
      cursor: pointer; font-size: 18px; display: flex;
      align-items: center; justify-content: center; transition: transform 0.2s;
    }
    .wakkii-radio-btn:hover { transform: scale(1.1); }
    .wakkii-radio-btn.play {
      background: linear-gradient(135deg, #E91E63, #9C27B0); color: white;
    }
    .wakkii-radio-btn.pl {
      background: #1a1a2e; color: #8888aa; border: 1px solid #9C27B0;
    }
    .wakkii-radio-playlist {
      max-height: 0; overflow: hidden; transition: max-height 0.3s ease;
      background: #1a1a2e; border-top: 1px solid #9C27B0;
    }
    .wakkii-radio-playlist.open { max-height: 300px; overflow-y: auto; }
    .wakkii-radio-playlist-header {
      padding: 8px 14px; font-size: 12px; font-weight: 600; color: white;
      display: flex; justify-content: space-between; align-items: center;
    }
    .wakkii-radio-playlist-time { font-size: 9px; color: #8888aa; font-weight: normal; }
    .wakkii-radio-playlist-item {
      padding: 6px 14px; font-size: 11px; color: #ccc;
      border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .wakkii-radio-playlist-empty {
      padding: 12px; font-size: 11px; color: #8888aa; text-align: center;
    }
    .wakkii-radio-footer {
      font-size: 8px; color: #555; text-align: center; padding: 4px;
    }
  `;
  document.head.appendChild(style);

  // Create widget
  const widget = document.createElement('div');
  widget.className = 'wakkii-radio';
  widget.innerHTML = `
    <div class="wakkii-radio-header" id="radioHeader">
      <span class="logo">📻</span>
      <div>
        <h3>V-103 Atlanta</h3>
        <div class="sub">The People's Station</div>
      </div>
      <span class="close" id="radioClose">✕</span>
    </div>
    <div class="wakkii-radio-body">
      <div class="wakkii-radio-status" id="radioStatus">Connecting...</div>
      <div class="wakkii-radio-eq paused" id="radioEq">
        <div class="bar"></div><div class="bar"></div><div class="bar"></div>
        <div class="bar"></div><div class="bar"></div><div class="bar"></div>
        <div class="bar"></div>
      </div>
      <div class="wakkii-radio-nowplaying">NOW PLAYING</div>
      <div class="wakkii-radio-song" id="radioSong">Loading...</div>
      <button class="wakkii-radio-save" id="radioSave">♡ Save to Playlist</button>
      <div class="wakkii-radio-controls">
        <button class="wakkii-radio-btn play" id="radioPlay">▶</button>
        <button class="wakkii-radio-btn pl" id="radioPlBtn">📋</button>
      </div>
    </div>
    <div class="wakkii-radio-playlist" id="radioPlaylist">
      <div class="wakkii-radio-playlist-header">
        <span>MY PLAYLIST</span>
        <span class="wakkii-radio-playlist-time" id="radioPlTime"></span>
      </div>
      <div id="radioPlItems"></div>
    </div>
    <div class="wakkii-radio-footer">24/7 · Live Stream</div>
  `;
  document.body.appendChild(widget);

  const statusEl = widget.querySelector('#radioStatus');
  const eqEl = widget.querySelector('#radioEq');
  const songEl = widget.querySelector('#radioSong');
  const saveBtn = widget.querySelector('#radioSave');
  const playBtn = widget.querySelector('#radioPlay');
  const plBtn = widget.querySelector('#radioPlBtn');
  const plEl = widget.querySelector('#radioPlaylist');
  const plItemsEl = widget.querySelector('#radioPlItems');
  const plTimeEl = widget.querySelector('#radioPlTime');
  const closeBtn = widget.querySelector('#radioClose');
  const headerEl = widget.querySelector('#radioHeader');

  // Drag to move
  let dragging = false, dragX = 0, dragY = 0;
  headerEl.addEventListener('mousedown', (e) => {
    dragging = true;
    dragX = e.clientX - widget.offsetLeft;
    dragY = e.clientY - widget.offsetTop;
    widget.style.transition = 'none';
  });
  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    widget.style.left = (e.clientX - dragX) + 'px';
    widget.style.top = (e.clientY - dragY) + 'px';
    widget.style.bottom = 'auto';
  });
  document.addEventListener('mouseup', () => { dragging = false; });

  // Close
  closeBtn.addEventListener('click', () => {
    widget.style.display = 'none';
    if (audio) { audio.pause(); isPlaying = false; }
  });

  // Play/pause
  playBtn.addEventListener('click', () => {
    if (isPlaying) {
      audio.pause();
      isPlaying = false;
      playBtn.textContent = '▶';
      statusEl.textContent = 'Paused';
      statusEl.classList.remove('live');
      eqEl.classList.add('paused');
    } else {
      if (!audio) {
        audio = new Audio(V103_URL);
        audio.crossOrigin = 'anonymous';
        audio.addEventListener('error', () => {
          statusEl.textContent = 'Reconnecting...';
          setTimeout(() => { if (isPlaying) audio.load(); }, 3000);
        });
      }
      audio.play().then(() => {
        isPlaying = true;
        playBtn.textContent = '⏸';
        statusEl.textContent = '● LIVE';
        statusEl.classList.add('live');
        eqEl.classList.remove('paused');
        fetchSongMeta();
      }).catch(() => {
        statusEl.textContent = 'Tap play again';
      });
    }
  });

  // Save to playlist
  saveBtn.addEventListener('click', () => {
    if (!currentSong) return;
    const exists = playlist.find(s => s.title === currentSong);
    if (exists) {
      playlist = playlist.filter(s => s.title !== currentSong);
      saveBtn.classList.remove('saved');
      saveBtn.textContent = '♡ Save to Playlist';
    } else {
      playlist.push({ title: currentSong, station: 'V-103 Atlanta', saved_at: new Date().toISOString() });
      saveBtn.classList.add('saved');
      saveBtn.textContent = '♥ Saved';
    }
    localStorage.setItem(PLAYLIST_KEY, JSON.stringify(playlist));
    if (showPlaylist) renderPlaylist();
  });

  // Toggle playlist
  plBtn.addEventListener('click', () => {
    showPlaylist = !showPlaylist;
    plEl.classList.toggle('open', showPlaylist);
    if (showPlaylist) renderPlaylist();
  });

  function renderPlaylist() {
    const now = new Date();
    const ctOffset = now.getTimezoneOffset() === 300 ? CT_OFFSET_SUMMER : CT_OFFSET_WINTER;
    const ctTime = new Date(now.getTime() + (ctOffset * 60000) - (now.getTimezoneOffset() * 60000));
    plTimeEl.textContent = ctTime.toLocaleString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true });

    if (playlist.length === 0) {
      plItemsEl.innerHTML = '<div class="wakkii-radio-playlist-empty">No songs saved yet</div>';
      return;
    }
    plItemsEl.innerHTML = playlist.slice(-15).reverse().map(s =>
      `<div class="wakkii-radio-playlist-item">♪ ${escapeHtml(s.title)}</div>`
    ).join('');
  }

  function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
  }

  // Fetch song metadata from ICY stream
  async function fetchSongMeta() {
    try {
      const resp = await fetch(V103_URL, {
        method: 'GET',
        headers: { 'Icy-MetaData': '1' },
        mode: 'cors'
      });
      const reader = resp.body.getReader();
      const metaint = parseInt(resp.headers.get('icy-metaint') || '2048');
      const { value: chunk1 } = await reader.read();
      if (chunk1.length >= metaint) {
        const ml = chunk1[metaint];
        if (ml > 0) {
          const meta = new TextDecoder().decode(chunk1.slice(metaint + 1, metaint + 1 + ml * 16));
          const match = meta.match(/StreamTitle='([^']*)'/);
          if (match && match[1]) {
            currentSong = match[1].trim();
            songEl.textContent = currentSong;
            updateSaveButton();
          }
        }
      }
      reader.cancel();
    } catch (e) {
      // CORS might block — try alternative method
    }
  }

  function updateSaveButton() {
    const exists = playlist.find(s => s.title === currentSong);
    if (exists) {
      saveBtn.classList.add('saved');
      saveBtn.textContent = '♥ Saved';
    } else {
      saveBtn.classList.remove('saved');
      saveBtn.textContent = '♡ Save to Playlist';
    }
  }

  // Poll for song changes every 30 seconds
  setInterval(() => {
    if (isPlaying) fetchSongMeta();
  }, 30000);

  // Auto-play on load
  setTimeout(() => {
    playBtn.click();
  }, 1000);

  window.WakkiiRadio = {
    play: () => { if (!isPlaying) playBtn.click(); },
    pause: () => { if (isPlaying) playBtn.click(); },
    toggle: () => playBtn.click(),
    show: () => { widget.style.display = 'block'; },
    hide: () => { widget.style.display = 'none'; },
  };
})();

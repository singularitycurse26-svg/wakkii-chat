/**
 * Aceline Walkie-Talki — Voice rooms with WebRTC (PeerJS)
 *
 * Based on Wakkii Links walkie-talki system from Soulmate OS.
 * Features:
 * - Push-to-talk (hold to speak) or open mode
 * - Room-based with 6-char codes
 * - Share via link + QR code
 * - Host/listener roles with raise hand
 * - Video support
 * - Presence tracking (heartbeats)
 * - Max 8 participants
 * - Auto-contact addition
 */

const PEER_PREFIX = 'aceline-';
const MAX_PARTICIPANTS = 8;
const HEARTBEAT_INTERVAL = 5000;
const PRESENCE_TTL = 15000;

class AcelineWalkieTalki {
  constructor(userName) {
    this.userName = userName || 'User';
    this.peer = null;
    this.stream = null;
    this.videoStream = null;
    this.connections = new Map();
    this.participants = new Map();
    this.videoCalls = new Map();
    this.audioElements = new Map();
    this.videoElements = new Map();
    this.roomId = '';
    this.isHost = false;
    this.mode = 'ptt';
    this.role = 'speaker';
    this.micEnabled = false;
    this.videoEnabled = false;
    this.connected = false;
    this.onError = null;
    this.onStateChange = null;
    this.onParticipantsChange = null;
  }

  generateRoomId() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let id = '';
    for (let i = 0; i < 6; i++) id += chars[Math.floor(Math.random() * chars.length)];
    return id;
  }

  getShareUrl() {
    if (!this.roomId) return '';
    const base = window.location.origin + window.location.pathname;
    return `${base}#aceline-${this.roomId}`;
  }

  async createRoom(mode = 'ptt', role = 'speaker') {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
        video: false
      });
      this.stream.getAudioTracks().forEach(t => t.enabled = false);

      this.roomId = this.generateRoomId();
      this.mode = mode;
      this.role = role;
      this.isHost = true;

      const peerId = `${PEER_PREFIX}${this.roomId}`;
      this.peer = new Peer(peerId, { debug: 1 });
      this.setupPeer();
      this.notifyStateChange();
    } catch (e) {
      this.notifyError('Microphone access denied: ' + e.message);
    }
  }

  async joinRoom(roomId, role = 'speaker') {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
        video: false
      });
      this.stream.getAudioTracks().forEach(t => t.enabled = false);

      this.roomId = roomId.toUpperCase().replace(/[^A-Z0-9]/g, '');
      this.role = role;
      this.isHost = false;

      const myPeerId = `${PEER_PREFIX}${this.roomId}-${Math.random().toString(36).slice(2, 8)}`;
      this.peer = new Peer(myPeerId, { debug: 1 });

      this.peer.on('open', () => {
        this.connected = true;
        this.participants.set(myPeerId, {
          peerId: myPeerId, name: this.userName, role, isHost: false,
          speaking: false, handRaised: false, muted: false, online: true,
          lastSeen: Date.now(), videoEnabled: false
        });
        this.notifyParticipantsChange();
        this.notifyStateChange();

        const hostPeerId = `${PEER_PREFIX}${this.roomId}`;
        this.connectToPeer(hostPeerId);
      });

      this.peer.on('connection', (conn) => this.handleConnection(conn));
      this.peer.on('call', (call) => this.handleCall(call));
      this.peer.on('error', (err) => {
        if (err.type === 'peer-unavailable') {
          this.notifyError('Room not found. Check the link and try again.');
        } else {
          this.notifyError(err.message || String(err));
        }
      });
      this.peer.on('disconnected', () => {
        this.connected = false;
        this.notifyStateChange();
        try { this.peer.reconnect(); } catch {}
      });

      this.startHeartbeat();
    } catch (e) {
      this.notifyError('Microphone access denied: ' + e.message);
    }
  }

  setupPeer() {
    this.peer.on('open', () => {
      this.connected = true;
      const peerId = this.peer.id;
      this.participants.set(peerId, {
        peerId, name: this.userName, role: this.role, isHost: this.isHost,
        speaking: false, handRaised: false, muted: false, online: true,
        lastSeen: Date.now(), videoEnabled: false
      });
      this.notifyParticipantsChange();
      this.notifyStateChange();
    });

    this.peer.on('connection', (conn) => this.handleConnection(conn));
    this.peer.on('call', (call) => this.handleCall(call));
    this.peer.on('error', (err) => {
      if (err.type === 'unavailable-id') {
        this.notifyError('Room already exists. Joining instead...');
      } else if (err.type !== 'peer-unavailable') {
        this.notifyError(err.message || String(err));
      }
    });
    this.peer.on('disconnected', () => {
      this.connected = false;
      this.notifyStateChange();
      try { this.peer.reconnect(); } catch {}
    });

    this.startHeartbeat();
  }

  handleConnection(conn) {
    if (this.participants.size >= MAX_PARTICIPANTS) {
      conn.on('open', () => conn.send({ type: 'room-full' }));
      conn.close();
      this.notifyError('Room is full (8 people max)');
      return;
    }

    conn.on('open', () => {
      conn.send({
        type: 'hello',
        name: this.userName,
        role: this.role,
        isHost: this.isHost
      });
    });

    conn.on('data', (data) => this.handleDataMessage(data, conn.peer));

    conn.on('close', () => {
      this.participants.delete(conn.peer);
      this.connections.delete(conn.peer);
      this.notifyParticipantsChange();
      this.broadcastRoster();
    });
  }

  handleCall(call) {
    const meta = call.metadata || {};
    if (meta.type === 'video') {
      if (!this.videoStream) { call.close(); return; }
      call.answer(this.videoStream);
      this.setupVideoCall(call, call.peer);
      return;
    }
    if (!this.stream) { call.close(); return; }
    call.answer(this.stream);
    this.setupAudioCall(call, call.peer);

    if (!this.participants.has(call.peer)) {
      const name = meta.name || 'Guest';
      this.participants.set(call.peer, {
        peerId: call.peer, name, role: meta.role || 'listener',
        isHost: false, speaking: false, handRaised: false,
        muted: meta.role !== 'speaker', online: true,
        lastSeen: Date.now(), videoEnabled: false
      });
      this.notifyParticipantsChange();
    }
  }

  setupAudioCall(call, peerId) {
    call.on('stream', (remoteStream) => {
      let audio = this.audioElements.get(peerId);
      if (!audio) {
        audio = new Audio();
        audio.autoplay = true;
        this.audioElements.set(peerId, audio);
      }
      audio.srcObject = remoteStream;
      audio.play().catch(() => {});

      if (!this.participants.has(peerId)) {
        this.participants.set(peerId, {
          peerId, name: 'Guest', role: 'listener', isHost: false,
          speaking: false, handRaised: false, muted: true,
          online: true, lastSeen: Date.now(), videoEnabled: false
        });
        this.notifyParticipantsChange();
      }
    });

    call.on('close', () => {
      this.participants.delete(peerId);
      this.connections.delete(peerId);
      const audio = this.audioElements.get(peerId);
      if (audio) { audio.srcObject = null; this.audioElements.delete(peerId); }
      this.notifyParticipantsChange();
    });

    this.connections.set(peerId, call);
  }

  setupVideoCall(call, peerId) {
    call.on('stream', (remoteStream) => {
      let video = this.videoElements.get(peerId);
      if (!video) {
        video = document.createElement('video');
        video.autoplay = true;
        video.playsInline = true;
        this.videoElements.set(peerId, video);
      }
      video.srcObject = remoteStream;
      video.play().catch(() => {});
      this.notifyParticipantsChange();
    });

    call.on('close', () => {
      const video = this.videoElements.get(peerId);
      if (video) { video.srcObject = null; this.videoElements.delete(peerId); }
      this.videoCalls.delete(peerId);
      this.notifyParticipantsChange();
    });

    this.videoCalls.set(peerId, call);
  }

  handleDataMessage(data, fromPeerId) {
    if (!data || typeof data !== 'object') return;

    switch (data.type) {
      case 'hello':
        this.participants.set(fromPeerId, {
          peerId: fromPeerId, name: data.name || 'Guest',
          role: data.role || 'listener', isHost: data.isHost || false,
          speaking: false, handRaised: false, muted: data.role !== 'speaker',
          online: true, lastSeen: Date.now(), videoEnabled: false
        });
        this.notifyParticipantsChange();
        this.broadcastRoster();
        break;

      case 'roster':
        if (Array.isArray(data.participants)) {
          data.participants.forEach(p => this.participants.set(p.peerId, p));
          this.notifyParticipantsChange();
        }
        break;

      case 'raise-hand':
        const p = this.participants.get(fromPeerId);
        if (p) { p.handRaised = data.raised; this.notifyParticipantsChange(); }
        break;

      case 'role-change':
        const p2 = this.participants.get(fromPeerId);
        if (p2) { p2.role = data.role; p2.muted = data.role !== 'speaker'; this.notifyParticipantsChange(); }
        break;

      case 'ptt-start':
      case 'ptt-stop':
        const p3 = this.participants.get(fromPeerId);
        if (p3) { p3.speaking = data.type === 'ptt-start'; this.notifyParticipantsChange(); }
        break;

      case 'heartbeat':
        const p4 = this.participants.get(fromPeerId);
        if (p4) { p4.online = true; p4.lastSeen = Date.now(); }
        break;

      case 'video-on':
      case 'video-off':
        const p5 = this.participants.get(fromPeerId);
        if (p5) { p5.videoEnabled = data.type === 'video-on'; this.notifyParticipantsChange(); }
        break;

      case 'room-full':
        this.notifyError('Room is full (8 people max)');
        break;
    }
  }

  connectToPeer(remotePeerId) {
    if (!this.peer || !this.stream) return;
    if (this.connections.has(remotePeerId)) return;

    const conn = this.peer.connect(remotePeerId, {
      metadata: { name: this.userName, role: this.role, isHost: this.isHost }
    });

    conn.on('open', () => {
      conn.send({ type: 'hello', name: this.userName, role: this.role, isHost: this.isHost });
      const call = this.peer.call(remotePeerId, this.stream, {
        metadata: { name: this.userName, role: this.role }
      });
      if (call) this.setupAudioCall(call, remotePeerId);
    });

    conn.on('data', (data) => this.handleDataMessage(data, remotePeerId));
    conn.on('close', () => {
      this.participants.delete(remotePeerId);
      this.connections.delete(remotePeerId);
      this.notifyParticipantsChange();
    });
  }

  broadcastRoster() {
    const roster = Array.from(this.participants.values());
    this.connections.forEach(conn => {
      try { if (conn.open) conn.send({ type: 'roster', participants: roster }); } catch {}
    });
  }

  pushToTalkStart() {
    if (this.stream) this.stream.getAudioTracks().forEach(t => t.enabled = true);
    this.micEnabled = true;
    this.connections.forEach(conn => {
      try { conn.send({ type: 'ptt-start' }); } catch {}
    });
    this.notifyStateChange();
  }

  pushToTalkStop() {
    if (this.stream) this.stream.getAudioTracks().forEach(t => t.enabled = false);
    this.micEnabled = false;
    this.connections.forEach(conn => {
      try { conn.send({ type: 'ptt-stop' }); } catch {}
    });
    this.notifyStateChange();
  }

  raiseHand(raised) {
    this.connections.forEach(conn => {
      try { conn.send({ type: 'raise-hand', raised }); } catch {}
    });
    const myPeerId = this.peer?.id;
    if (myPeerId) {
      const me = this.participants.get(myPeerId);
      if (me) { me.handRaised = raised; this.notifyParticipantsChange(); }
    }
  }

  approveSpeaker(peerId) {
    const conn = this.connections.get(peerId);
    if (conn) { try { conn.send({ type: 'role-change', role: 'speaker' }); } catch {} }
    const p = this.participants.get(peerId);
    if (p) { p.role = 'speaker'; p.muted = false; p.handRaised = false; this.notifyParticipantsChange(); }
  }

  async toggleVideo() {
    if (this.videoEnabled) {
      if (this.videoStream) {
        this.videoStream.getTracks().forEach(t => t.stop());
        this.videoStream = null;
      }
      this.videoCalls.forEach(c => { try { c.close(); } catch {} });
      this.videoCalls.clear();
      this.videoElements.forEach(v => v.srcObject = null);
      this.videoElements.clear();
      this.connections.forEach(conn => { try { conn.send({ type: 'video-off' }); } catch {} });
      this.videoEnabled = false;
    } else {
      try {
        this.videoStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
          audio: false
        });
        this.connections.forEach(conn => { try { conn.send({ type: 'video-on' }); } catch {} });
        this.videoEnabled = true;
        this.broadcastVideo();
      } catch (e) {
        this.notifyError('Camera access denied: ' + e.message);
      }
    }
    this.notifyStateChange();
  }

  broadcastVideo() {
    if (!this.peer || !this.videoStream) return;
    this.participants.forEach((p, peerId) => {
      if (peerId === this.peer.id) return;
      if (this.videoCalls.has(peerId)) return;
      try {
        const call = this.peer.call(peerId, this.videoStream, {
          metadata: { type: 'video', name: this.userName }
        });
        if (call) this.setupVideoCall(call, peerId);
      } catch {}
    });
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      this.connections.forEach(conn => {
        try { if (conn.open) conn.send({ type: 'heartbeat', name: this.userName, ts: Date.now() }); } catch {}
      });
    }, HEARTBEAT_INTERVAL);

    this.presenceInterval = setInterval(() => {
      const now = Date.now();
      let changed = false;
      this.participants.forEach(p => {
        const wasOnline = p.online;
        p.online = wasOnline && (now - p.lastSeen < PRESENCE_TTL);
        if (wasOnline !== p.online) changed = true;
      });
      if (changed) this.notifyParticipantsChange();
    }, 3000);
  }

  leaveRoom() {
    this.connections.forEach(c => { try { c.close(); } catch {} });
    this.connections.clear();
    this.videoCalls.forEach(c => { try { c.close(); } catch {} });
    this.videoCalls.clear();
    this.participants.clear();
    this.audioElements.forEach(a => a.srcObject = null);
    this.audioElements.clear();
    this.videoElements.forEach(v => v.srcObject = null);
    this.videoElements.clear();

    if (this.stream) { this.stream.getTracks().forEach(t => t.stop()); this.stream = null; }
    if (this.videoStream) { this.videoStream.getTracks().forEach(t => t.stop()); this.videoStream = null; }
    if (this.peer) { try { this.peer.destroy(); } catch {} this.peer = null; }

    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
    if (this.presenceInterval) clearInterval(this.presenceInterval);

    this.roomId = '';
    this.isHost = false;
    this.connected = false;
    this.micEnabled = false;
    this.videoEnabled = false;
    this.notifyStateChange();
    this.notifyParticipantsChange();
  }

  getParticipants() {
    return Array.from(this.participants.values());
  }

  getState() {
    return {
      roomId: this.roomId,
      isHost: this.isHost,
      connected: this.connected,
      micEnabled: this.micEnabled,
      videoEnabled: this.videoEnabled,
      mode: this.mode,
      role: this.role
    };
  }

  notifyStateChange() {
    if (this.onStateChange) this.onStateChange(this.getState());
  }

  notifyParticipantsChange() {
    if (this.onParticipantsChange) this.onParticipantsChange(this.getParticipants());
  }

  notifyError(msg) {
    if (this.onError) this.onError(msg);
  }
}

// Export for use in index.html
window.AcelineWalkieTalki = AcelineWalkieTalki;

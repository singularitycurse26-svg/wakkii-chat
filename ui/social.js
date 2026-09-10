/**
 * Aceline Social UI — Live, Messaging, Contacts, Following, Payments
 *
 * Handles:
 * - Go Live (start/stop broadcasting, watch live streams)
 * - Live chat during broadcasts
 * - Direct messaging (DMs)
 * - Follow/unfollow users
 * - Contact list (auto-filing from calls)
 * - Wallet payments (send, request, on-ramp, off-ramp)
 * - Aceline AI voice assistant on walkie-talki
 */

const Social = {
  userId: null,
  username: null,
  walletAddress: null,

  init(userId, username, walletAddress) {
    this.userId = userId;
    this.username = username;
    this.walletAddress = walletAddress;
    this.createProfile();
  },

  async api(path, method = 'GET', body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const resp = await fetch(`${API_BASE}${path}`, opts);
    return resp.json();
  },

  async createProfile() {
    if (!this.userId || !this.username) return;
    await this.api('/social/profile', 'POST', {
      user_id: this.userId,
      username: this.username,
      display_name: this.username
    });
  },

  // --- Live Broadcasting ---

  async goLive(title) {
    return this.api('/live/go_live', 'POST', { user_id: this.userId, title: title || 'Live' });
  },

  async endLive() {
    return this.api('/live/end', 'POST', { user_id: this.userId });
  },

  async getLiveBroadcasts() {
    return this.api('/live/broadcasts');
  },

  async sendLiveChat(roomId, text) {
    return this.api('/live/chat/send', 'POST', {
      room_id: roomId, sender_id: this.userId, sender_name: this.username, text
    });
  },

  async getLiveChat(roomId) {
    return this.api(`/live/chat/${roomId}`);
  },

  // --- Following ---

  async follow(followingId) {
    return this.api('/social/follow', 'POST', { follower_id: this.userId, following_id: followingId });
  },

  async unfollow(followingId) {
    return this.api('/social/unfollow', 'POST', { follower_id: this.userId, following_id: followingId });
  },

  async getFollowing() {
    return this.api(`/social/following/${this.userId}`);
  },

  async getFollowers() {
    return this.api(`/social/followers/${this.userId}`);
  },

  // --- Contacts ---

  async getContacts() {
    return this.api(`/social/contacts/${this.userId}`);
  },

  async addContact(contactId, contactName, contactUsername, source = 'manual') {
    return this.api('/social/contacts/add', 'POST', {
      owner_id: this.userId, contact_id: contactId,
      contact_name: contactName, contact_username: contactUsername, source
    });
  },

  async autoAddContact(contactId, contactName, contactUsername, callType) {
    return this.api('/social/contacts/auto', 'POST', {
      owner_id: this.userId, owner_name: this.username,
      contact_id: contactId, contact_name: contactName,
      contact_username: contactUsername, call_type: callType
    });
  },

  // --- Messaging ---

  async sendMessage(receiverId, text) {
    return this.api('/social/messages/send', 'POST', {
      sender_id: this.userId, receiver_id: receiverId, text
    });
  },

  async getMessages(otherId) {
    return this.api(`/social/messages/${this.userId}/${otherId}`);
  },

  async getConversations() {
    return this.api(`/social/conversations/${this.userId}`);
  },

  async getUnreadCount() {
    return this.api(`/social/unread/${this.userId}`);
  },

  // --- Search ---

  async searchUsers(query) {
    return this.api(`/social/search?q=${encodeURIComponent(query)}`);
  },

  // --- Payments ---

  async sendFunds(receiverId, receiverAddress, amount, token = 'INC', memo = '') {
    return this.api('/payments/send', 'POST', {
      sender_id: this.userId, sender_address: this.walletAddress,
      receiver_id: receiverId, receiver_address: receiverAddress,
      amount, token, memo
    });
  },

  async requestFunds(amount, token = 'INC', memo = '') {
    return this.api('/payments/request', 'POST', {
      requester_id: this.userId, requester_address: this.walletAddress,
      amount, token, memo
    });
  },

  async getFundRequests() {
    return this.api(`/payments/requests/${this.userId}`);
  },

  async onRamp(fiatAmount, currency = 'USD') {
    return this.api('/payments/onramp', 'POST', {
      user_id: this.userId, user_address: this.walletAddress,
      fiat_amount: fiatAmount, fiat_currency: currency
    });
  },

  async offRamp(cryptoAmount, token = 'INC') {
    return this.api('/payments/offramp', 'POST', {
      user_id: this.userId, user_address: this.walletAddress,
      crypto_amount: cryptoAmount, crypto_token: token
    });
  },

  async getTransactionHistory() {
    return this.api(`/payments/history/${this.userId}`);
  }
};

window.Social = Social;

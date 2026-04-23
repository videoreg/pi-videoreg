const SmsInboxComponent = {
  components: { TabSwitch, Icon },
  template: `
    <div>
      <div class="page-header">
        <h1 class="page-title">{{ $t('http.sms_inbox.title') }}</h1>
        <div style="display: flex; gap: var(--spacing-sm);">
          <div v-if="loading" class="spinner spinner-sm"></div>
          <button v-else class="btn btn-icon" @click="load" :title="$t('http.common.refresh')">↻</button>
        </div>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div v-if="messages.length === 0 && !loading" class="alert alert-info">
        {{ $t('http.sms_inbox.no_messages') }}
      </div>

      <template v-if="messages.length > 0">
        <tab-switch
          v-model="activeDate"
          :tabs="dateTabs"
          style="margin-bottom: var(--spacing-lg);"
        />

        <div
          v-for="msg in activeMessages"
          :key="msg.filename"
          class="media-feed-item"
          style="display: block;"
        >
          <div class="media-feed-info" style="padding: var(--spacing-md);">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-sm); margin-bottom: var(--spacing-sm);">
              <span style="font-weight: 600; color: var(--color-text-primary);">{{ msg.number }}</span>
              <div style="display: flex; align-items: center; gap: var(--spacing-sm);">
                <span style="font-size: 0.8125rem; color: var(--color-text-secondary);">{{ formatTime(msg.timestamp) }}</span>
                <button
                  class="btn-icon"
                  style="color: var(--color-error); opacity: 0.7; padding: 2px;"
                  :title="$t('common.delete')"
                  @click="deleteMsg(msg)"
                ><icon name="delete" :size="20"></icon></button>
              </div>
            </div>
            <div style="color: var(--color-text-secondary); font-size: 0.9375rem; white-space: pre-wrap; word-break: break-word;">{{ msg.text }}</div>
          </div>
        </div>
      </template>
    </div>
  `,

  data() {
    return {
      messages: [],
      activeDate: null,
      error: '',
      loading: false
    };
  },

  computed: {
    dates() {
      const s = new Set();
      for (const msg of this.messages) {
        s.add(msg.timestamp.slice(0, 10));
      }
      return [...s].sort().reverse();
    },

    dateTabs() {
      return this.dates.map(d => ({ value: d, label: this.formatDateTab(d) }));
    },

    activeMessages() {
      if (!this.activeDate) return [];
      return this.messages.filter(m => m.timestamp.slice(0, 10) === this.activeDate);
    }
  },

  methods: {
    async load() {
      this.error = '';
      this.loading = true;
      try {
        const response = await fetch('/api/sms', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('http.sms_inbox.error_load');
          return;
        }
        this.messages = data.messages || [];
        this.activeDate = this.dates[0] || null;
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    },

    formatTime(timestamp) {
      if (!timestamp) return '—';
      try {
        const normalized = timestamp.replace(/([+-]\d{2})$/, '$1:00');
        const d = new Date(normalized);
        return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      } catch (e) {
        return timestamp;
      }
    },

    formatDateTab(dateStr) {
      try {
        const d = new Date(dateStr + 'T00:00:00');
        return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', weekday: 'short' });
      } catch (e) {
        return dateStr;
      }
    },

    async deleteMsg(msg) {
      if (!confirm(this.$t('http.sms_inbox.confirm_delete', { number: msg.number }))) return;
      try {
        const response = await fetch(`/api/sms/${encodeURIComponent(msg.filename)}`, {
          method: 'DELETE',
          credentials: 'same-origin'
        });
        if (!response.ok) {
          const data = await response.json();
          this.error = data.error || this.$t('http.sms_inbox.error_delete');
          return;
        }
        this.messages = this.messages.filter(m => m.filename !== msg.filename);
        if (this.activeMessages.length === 0) {
          this.activeDate = this.dates[0] || null;
        }
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      }
    }
  },

  async mounted() {
    await this.load();
  }
};

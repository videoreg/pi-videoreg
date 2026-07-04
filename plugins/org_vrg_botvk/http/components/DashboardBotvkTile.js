// Dashboard tile: VK bot status.
// Data: botvk.get_status → { configured, healthy, last_error, last_ok_at }.
const DashboardBotvkTile = {
  components: { Icon, Shimmer },
  emits: ['navigate'],
  props: {
    data: { type: Object, default: null },
    loading: { type: Boolean, default: false },
  },

  template: `
    <div v-if="loading && !data" class="dashboard-tile">
      <div class="dashboard-tile-header">
        <shimmer height="20px" width="20px" style="border-radius: 4px; flex-shrink: 0;"></shimmer>
        <shimmer height="15px" width="45%"></shimmer>
      </div>
      <shimmer height="13px" width="60%"></shimmer>
    </div>
    <div v-else-if="data" class="dashboard-tile" @click="$emit('navigate', 'vk')">
      <div class="dashboard-tile-header">
        <span class="dashboard-tile-icon"><icon name="vk" :size="20"></icon></span>
        <span class="dashboard-tile-title">{{ $t('botvk.vk.menu') }}</span>
        <span class="status-indicator" style="margin-left: auto;">
          <span class="status-dot" :class="{ active: data.healthy }"></span>
          <span>{{ statusLabel }}</span>
        </span>
      </div>
      <div v-if="!data.configured" class="dashboard-tile-meta">{{ $t('http.home.bot_not_configured') }}</div>
      <div v-else-if="data.last_error" class="dashboard-tile-meta">{{ data.last_error }}</div>
      <div v-else-if="lastOkLabel" class="dashboard-tile-meta">{{ lastOkLabel }}</div>
    </div>
  `,

  computed: {
    statusLabel() {
      if (!this.data) return '—';
      if (!this.data.configured) return this.$t('http.home.bot_not_configured_short');
      if (this.data.healthy) return this.$t('http.home.bot_connected');
      return this.$t('http.home.bot_no_connection');
    },

    lastOkLabel() {
      if (!this.data?.last_ok_at) return '';
      const time = new Date(this.data.last_ok_at * 1000).toLocaleTimeString(VrgI18n.locale);
      return this.$t('http.home.bot_last_update', { time });
    },
  },
};

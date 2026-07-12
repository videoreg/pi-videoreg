// Dashboard tile: WiFi status. Data: net.connections → { wifi, ap, ... }.
const DashboardWifiTile = {
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
      <shimmer height="13px" width="70%"></shimmer>
      <shimmer height="13px" width="50%"></shimmer>
    </div>
    <div v-else class="dashboard-tile" @click="$emit('navigate', 'wifi')">
      <div class="dashboard-tile-header">
        <span class="dashboard-tile-icon"><icon :name="wifiIcon" :size="20"></icon></span>
        <span class="dashboard-tile-title">WiFi</span>
        <span class="status-indicator" style="margin-left: auto;">
          <span class="status-dot" :class="{ active: !!wifiType }"></span>
          <span>{{ statusText }}</span>
        </span>
      </div>
      <template v-if="wifiType">
        <div v-if="wifiSsid" class="dashboard-tile-row">
          <span class="dashboard-tile-label">SSID</span>
          <span>{{ wifiSsid }}</span>
        </div>
        <div class="dashboard-tile-row">
          <span class="dashboard-tile-label">{{ $t('http.home.type_label') }}</span>
          <span>{{ wifiType }}</span>
        </div>
        <div v-if="wifiIp" class="dashboard-tile-row">
          <span class="dashboard-tile-label">IP</span>
          <span>{{ wifiIp }}</span>
        </div>
      </template>
    </div>
  `,

  computed: {
    // After loading, a null `data` means the block did not resolve (its api call
    // errored or timed out) — not that WiFi is off. Show a neutral "no data"
    // state instead of a false "disconnected", which the several slow nmcli
    // calls at boot / first page load would otherwise trigger.
    statusText() {
      if (!this.data) return this.$t('http.home.no_data');
      return this.wifiType ? this.$t('http.home.connected') : this.$t('http.home.disconnected');
    },

    wifiIcon() {
      return (this.data?.wifi?.enabled || this.data?.ap?.enabled) ? 'wifi' : 'wifi_off';
    },

    wifiSsid() {
      if (this.data?.ap?.enabled) return this.data?.ap?.ssid || null;
      return this.data?.wifi?.ssid || null;
    },

    wifiType() {
      if (!this.data?.ap?.enabled && !this.data?.wifi?.enabled) return null;
      return (this.data?.ap?.enabled && !this.data?.wifi?.enabled) ? 'Access Point' : 'Client';
    },

    wifiIp() {
      return this.data?.wifi?.ip || this.data?.ap?.ip || null;
    },
  },
};

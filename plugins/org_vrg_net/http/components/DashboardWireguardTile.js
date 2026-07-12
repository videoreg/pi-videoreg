// Dashboard tile: WireGuard status. Data: net.wg_show → { active, ip_address }.
const DashboardWireguardTile = {
  components: { Icon, Shimmer },
  emits: ['navigate'],
  props: {
    data: { type: Object, default: null },
    loading: { type: Boolean, default: false },
  },

  computed: {
    // After loading, a null `data` means the block did not resolve (its api call
    // errored or timed out) — not that the tunnel is down. Show a neutral "no
    // data" state instead of a false "inactive": net.wg_show shells out to sudo
    // wg/ip, which can be slow at boot / first page load.
    active() { return !!(this.data && this.data.active); },
    statusText() {
      if (!this.data) return this.$t('http.home.no_data');
      return this.active ? this.$t('http.home.wg_active') : this.$t('http.home.wg_inactive');
    },
  },

  template: `
    <div v-if="loading && !data" class="dashboard-tile">
      <div class="dashboard-tile-header">
        <shimmer height="20px" width="20px" style="border-radius: 4px; flex-shrink: 0;"></shimmer>
        <shimmer height="15px" width="55%"></shimmer>
      </div>
      <shimmer height="13px" width="50%"></shimmer>
    </div>
    <div v-else class="dashboard-tile" @click="$emit('navigate', 'wireguard')">
      <div class="dashboard-tile-header">
        <span class="dashboard-tile-icon"><icon name="vpn" :size="20"></icon></span>
        <span class="dashboard-tile-title">WireGuard</span>
        <span class="status-indicator" style="margin-left: auto;">
          <span class="status-dot" :class="{ active: active }"></span>
          <span>{{ statusText }}</span>
        </span>
      </div>
      <template v-if="active">
        <div v-if="data.ip_address" class="dashboard-tile-row">
          <span class="dashboard-tile-label">IP</span>
          <span>{{ data.ip_address }}</span>
        </div>
      </template>
    </div>
  `,
};

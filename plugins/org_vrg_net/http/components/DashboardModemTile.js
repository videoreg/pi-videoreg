// Dashboard tile: modem connectivity.
// Data: net.modem_dashboard → { connected, model, operator, access_tech, ip }.
const DashboardModemTile = {
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
        <shimmer height="15px" width="50%"></shimmer>
      </div>
      <shimmer height="13px" width="65%"></shimmer>
      <shimmer height="13px" width="55%"></shimmer>
      <shimmer height="13px" width="45%"></shimmer>
    </div>
    <div v-else class="dashboard-tile" @click="$emit('navigate', 'modem')">
      <div class="dashboard-tile-header">
        <span class="dashboard-tile-icon"><icon :name="data && data.connected ? 'modem' : 'modem_off'" :size="20"></icon></span>
        <span class="dashboard-tile-title">{{ $t('net.settings.modem') }}</span>
        <span class="status-indicator" style="margin-left: auto;">
          <span class="status-dot" :class="{ active: !!(data && data.connected) }"></span>
          <span>{{ data && data.connected ? $t('http.home.enabled') : $t('http.home.disabled') }}</span>
        </span>
      </div>
      <template v-if="data && data.connected">
        <div v-if="data.model" class="dashboard-tile-row">
          <span class="dashboard-tile-label">{{ $t('http.home.model_label') }}</span>
          <span>{{ data.model }}</span>
        </div>
        <div v-if="data.operator" class="dashboard-tile-row">
          <span class="dashboard-tile-label">Operator:</span>
          <span>{{ data.operator }}<template v-if="data.access_tech"> · {{ data.access_tech }}</template></span>
        </div>
        <div v-if="data.ip" class="dashboard-tile-row">
          <span class="dashboard-tile-label">IP</span>
          <span>{{ data.ip }}</span>
        </div>
      </template>
    </div>
  `,
};

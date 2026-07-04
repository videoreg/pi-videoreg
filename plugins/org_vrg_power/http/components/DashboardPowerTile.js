// Dashboard tile: power/battery status.
// Data: power.get_status → { charging, source, battery_percent, uptime }.
const DashboardPowerTile = {
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
      <shimmer height="13px" width="60%"></shimmer>
      <shimmer height="13px" width="45%"></shimmer>
    </div>
    <div v-else class="dashboard-tile" @click="$emit('navigate', 'power')">
      <div class="dashboard-tile-header">
        <span class="dashboard-tile-icon"><icon :name="powerIcon" :size="20"></icon></span>
        <span class="dashboard-tile-title">{{ $t('power.settings.power') }}</span>
        <span v-if="data" class="status-indicator" style="margin-left: auto;">
          <span class="status-dot" :class="{ active: data.charging }"></span>
          <span>{{ data.charging ? $t('http.home.charging') : $t('http.home.on_battery') }}</span>
        </span>
      </div>
      <template v-if="data">
        <div v-if="data.source" class="dashboard-tile-row">
          <span class="dashboard-tile-label">{{ $t('http.home.type_label') }}</span>
          <span>{{ data.source.title }}</span>
        </div>
        <div v-if="data.source && data.source.battery_telemetry" class="dashboard-tile-row">
          <span class="dashboard-tile-label">{{ $t('http.home.charge_label') }}</span>
          <strong>{{ data.battery_percent }}%</strong>
        </div>
        <div v-if="data.uptime != null" class="dashboard-tile-row">
          <span class="dashboard-tile-label">{{ $t('power.power.uptime_label') }}</span>
          <span>{{ uptimeLabel }}</span>
        </div>
      </template>
      <div v-else class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
    </div>
  `,

  computed: {
    powerIcon() {
      if (!this.data) return 'battery';
      if (!this.data?.source?.battery_telemetry) return 'power_plug';
      return this.data.charging ? 'battery_charging' : 'battery';
    },

    uptimeLabel() {
      const sec = this.data?.uptime;
      if (sec == null) return '—';
      const h = Math.floor(sec / 3600);
      const m = Math.floor(sec / 60) % 60;
      if (h > 0) return m > 0 ? this.$t('http.trips.duration_h_m', { h, m }) : this.$t('http.trips.duration_h', { h });
      return this.$t('http.trips.duration_min', { m: Math.max(m, 1) });
    },
  },
};

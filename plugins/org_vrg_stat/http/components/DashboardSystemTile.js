// Dashboard tile: system stats. Data: stat.get_current_temp → { cpu_temp }.
const DashboardSystemTile = {
  components: { Icon, Shimmer },
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
    <div v-else class="dashboard-tile" style="cursor: default;">
      <div class="dashboard-tile-header">
        <span class="dashboard-tile-icon"><icon name="core" :size="20"></icon></span>
        <span class="dashboard-tile-title">{{ $t('http.home.system_title') }}</span>
      </div>
      <div class="dashboard-tile-row">
        <span class="dashboard-tile-label">{{ $t('http.home.cpu_temp_label') }}</span>
        <span>{{ cpuTempLabel }}</span>
      </div>
    </div>
  `,

  computed: {
    cpuTempLabel() {
      const temp = this.data?.cpu_temp;
      if (temp == null) return '—';
      return temp + ' °C';
    },
  },
};

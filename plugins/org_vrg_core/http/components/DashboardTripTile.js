// Dashboard tile: current trip state. Data: core.get_trip_state → { state, start }.
const DashboardTripTile = {
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
        <shimmer height="15px" width="55%"></shimmer>
      </div>
      <shimmer height="14px" width="80%"></shimmer>
      <shimmer height="12px" width="55%"></shimmer>
    </div>
    <div v-else class="dashboard-tile" :class="data && data.state ? 'dashboard-tile--' + data.state : ''" @click="$emit('navigate', 'trips')">
      <div class="dashboard-tile-header">
        <span class="dashboard-tile-icon"><icon name="gps_tracks" :size="20"></icon></span>
        <span class="dashboard-tile-title">{{ $t('http.home.trip_title') }}</span>
      </div>
      <template v-if="data && data.state">
        <div class="dashboard-tile-row">{{ tripDurationLabel }}</div>
        <div class="dashboard-tile-meta">{{ $t('http.trips.time_from', { time: tripStartLabel }) }}</div>
      </template>
      <div v-else class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
    </div>
  `,

  computed: {
    tripDurationLabel() {
      if (!this.data?.state || !this.data?.start) return '';
      const prefix = this.data.state === 'in_trip' ? this.$t('http.home.trip_in_progress') : this.$t('http.home.trip_parked');
      return prefix + ': ' + this._formatDuration(this.data.start);
    },

    tripStartLabel() {
      if (!this.data?.start) return '';
      const d = new Date(this.data.start);
      return d.toLocaleTimeString(VrgI18n.locale, { hour: '2-digit', minute: '2-digit' }) + ' ' + d.toLocaleDateString(VrgI18n.locale, { day: 'numeric', month: 'long' });
    },
  },

  methods: {
    _formatDuration(startIso) {
      const start = new Date(startIso);
      const diffMin = Math.floor((Date.now() - start) / 60000);
      if (diffMin < 1) return this.$t('http.trips.less_than_min');
      if (diffMin < 60) return this.$t('http.trips.duration_min', { m: diffMin });
      const h = Math.floor(diffMin / 60);
      const m = diffMin % 60;
      return m > 0 ? this.$t('http.trips.duration_h_m', { h, m }) : this.$t('http.trips.duration_h', { h });
    },
  },
};

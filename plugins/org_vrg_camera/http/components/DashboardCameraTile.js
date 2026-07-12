// Dashboard tile: camera status. Data: camera.get_info → { model, video_state, thermal_status }.
const DashboardCameraTile = {
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
      <shimmer height="13px" width="65%"></shimmer>
    </div>
    <div v-else class="dashboard-tile" @click="$emit('navigate', 'camera')">
      <div class="dashboard-tile-header">
        <span class="dashboard-tile-icon"><icon name="camera" :size="20"></icon></span>
        <span class="dashboard-tile-title">{{ $t('camera.settings.camera') }}</span>
        <span v-if="data" class="status-indicator" style="margin-left: auto;">
          <span class="status-dot" :class="{ active: data.video_state === 'record' }"></span>
          <span>{{ cameraStateLabel }}</span>
        </span>
      </div>
      <template v-if="data">
        <div class="dashboard-tile-row">
          <span class="dashboard-tile-label">{{ $t('http.home.model_label') }}</span>
          <span>{{ data.model || $t('http.home.camera_no_found_short') }}</span>
        </div>
        <div class="dashboard-tile-row">
          <span class="dashboard-tile-label">{{ $t('http.home.thermal_label') }}</span>
          <span>{{ thermalStatusLabel }}</span>
        </div>
      </template>
      <div v-else class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
    </div>
  `,

  computed: {
    cameraStateLabel() {
      if (!this.data) return '—';
      const labels = {
        record: this.$t('camera.camera.state_record'),
        pause: this.$t('camera.camera.state_pause'),
        stop: this.$t('camera.camera.state_stop'),
      };
      return labels[this.data.video_state] || '—';
    },

    thermalStatusLabel() {
      const labels = {
        normal: this.$t('camera.camera.thermal_normal'),
        downscaled: this.$t('camera.camera.thermal_downscaled'),
        overheated: this.$t('camera.camera.thermal_overheated'),
      };
      return labels[this.data?.thermal_status] || '—';
    },
  },
};

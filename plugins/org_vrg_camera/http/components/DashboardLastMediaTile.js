// Dashboard tile: preview of the last captured media.
// Data: camera.get_last_media → { item: { type, name, datetime, preview, ready } }.
const DashboardLastMediaTile = {
  components: { TripsMediaItem, Shimmer },
  inject: ['appStatusOffline', 'appStatusLastUpdated'],
  props: {
    data: { type: Object, default: null },
    loading: { type: Boolean, default: false },
  },

  template: `
    <div v-if="loading && !data" class="dashboard-tile dashboard-tile--media">
      <shimmer class="shimmer-media"></shimmer>
    </div>
    <div v-else-if="mediaItem" class="dashboard-tile dashboard-tile--media">
      <trips-media-item :item="mediaItem" :initial-video-ready="mediaReady"></trips-media-item>
      <div class="dashboard-media-badge">{{ badgeLabel }}</div>
    </div>
  `,

  computed: {
    mediaItem() {
      const item = this.data?.item;
      if (!item) return null;
      const result = {
        type: item.type,
        filename: item.type === 'video' ? item.name + '.h264' : item.name + '.jpg',
        date: item.datetime,
      };
      if (item.type === 'video' && item.preview) {
        result.screenshot = item.preview + '.jpg';
      }
      return result;
    },

    mediaReady() {
      return this.data?.item?.ready === true;
    },

    lastUpdatedLabel() {
      if (!this.appStatusLastUpdated) return null;
      return this.appStatusLastUpdated.toLocaleTimeString(VrgI18n.locale, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    },

    badgeLabel() {
      if (this.appStatusOffline && this.lastUpdatedLabel) {
        return this.$t('http.home.badge_last_updated', { time: this.lastUpdatedLabel });
      }
      return this.$t('http.home.badge_now');
    },
  },
};

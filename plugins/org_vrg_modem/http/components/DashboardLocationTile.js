// Dashboard tile: last known location. Data: modem.get_location → { gps, lbs }.
const DashboardLocationTile = {
  components: { Icon, Shimmer },
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
    <div v-else class="dashboard-tile" style="cursor: default;">
      <div class="dashboard-tile-header">
        <span class="dashboard-tile-icon"><icon name="map" :size="20"></icon></span>
        <span class="dashboard-tile-title">{{ $t('http.home.location_title') }}</span>
        <span class="status-indicator" style="margin-left: auto;">
          <span class="status-dot" :class="{ active: locationOn }"></span>
          <span>{{ locationOn ? $t('http.home.location_on') : $t('http.home.location_unknown') }}</span>
        </span>
      </div>
      <div v-if="gpsLocation" class="dashboard-tile-row">
        <span class="dashboard-tile-label">GPS</span>
        <span style="display:flex; align-items:center; gap:4px;">
          <a :href="gpsLocation.url" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">{{ gpsLocation.label }}</a>
          <button @click="copyToClipboard(gpsLocation.coords)" class="btn btn-ghost btn-sm" :title="$t('http.app.copy_coords')"><icon name="copy" :size="16"></icon></button>
        </span>
      </div>
      <div v-if="lbsLocation" class="dashboard-tile-row">
        <span class="dashboard-tile-label">LBS</span>
        <span style="display:flex; align-items:center; gap:4px;">
          <a :href="lbsLocation.url" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">{{ lbsLocation.label }}</a>
          <button @click="copyToClipboard(lbsLocation.coords)" class="btn btn-ghost btn-sm" :title="$t('http.app.copy_coords')"><icon name="copy" :size="16"></icon></button>
        </span>
      </div>
      <div v-if="!gpsLocation && !lbsLocation" class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
    </div>
  `,

  computed: {
    gpsLocation() {
      return this._toLocation(this.data?.gps, 'GPS');
    },

    lbsLocation() {
      return this._toLocation(this.data?.lbs, 'LBS');
    },

    locationOn() {
      return !!(this.gpsLocation || this.lbsLocation);
    },
  },

  methods: {
    _toLocation(src, label) {
      const lat = parseFloat(src?.latitude);
      const lng = parseFloat(src?.longitude);
      if (!isFinite(lat) || !isFinite(lng)) return null;
      return {
        url: `https://yandex.ru/maps/?mode=search&text=${lat}%2C${lng}`,
        label: `${label}: ${lat.toFixed(2)}, ${lng.toFixed(2)}`,
        coords: `${lat}, ${lng}`,
      };
    },

    async copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text);
      } catch (e) {
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
      }
    },
  },
};

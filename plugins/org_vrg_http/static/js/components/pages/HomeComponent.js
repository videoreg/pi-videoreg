// Home page component — dashboard with Now block + 5 status tiles
const HomeComponent = {
  emits: ['navigate'],
  components: { Icon, TripsMediaItem },
  inject: ['appStatusData', 'appStatusOffline', 'appStatusLastUpdated'],

  template: `
    <div>
      <div class="page-header">
        <h1 class="page-title">{{ $t('http.home.title') }}</h1>
        <div style="display: flex; gap: var(--spacing-sm);">
          <div v-if="loading" class="spinner spinner-sm"></div>
          <button v-else class="btn btn-icon" @click="load" :title="$t('http.common.refresh')">↻</button>
        </div>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <!-- Row 1: Now + Trip -->
      <div class="dashboard-grid-now">

        <!-- Now block -->
        <div v-if="loading" class="vrg-state-block">
          <div class="vrg-state-header">
            <shimmer height="14px" width="80px"></shimmer>
          </div>
          <div class="vrg-state-content">
            <div class="vrg-state-media">
              <shimmer class="shimmer-media"></shimmer>
            </div>
            <div class="vrg-state-info">
              <shimmer height="32px" width="75%"></shimmer>
              <shimmer height="32px" width="60%"></shimmer>
              <shimmer height="32px" width="80%"></shimmer>
            </div>
          </div>
        </div>
        <div v-else class="vrg-state-block">
          <div class="vrg-state-header">
            <span class="vrg-state-section-title">{{ $t('http.now') }}</span>
            <span v-if="appStatusOffline && statusLastUpdatedLabel" class="vrg-state-last-updated">{{ $t('http.app.last_updated', {time: statusLastUpdatedLabel}) }}</span>
          </div>
          <div class="vrg-state-content">
            <div v-if="statusLastMediaItem" class="vrg-state-media">
              <trips-media-item
                :item="statusLastMediaItem"
                :initial-video-ready="statusLastMediaReady"
              ></trips-media-item>
            </div>
            <div class="vrg-state-info">
              <div class="vrg-state-links">
                <div v-if="gpsLocation" class="vrg-state-location-row">
                  <a :href="gpsLocation.url" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">{{ gpsLocation.label }}</a>
                  <button @click="copyToClipboard(gpsLocation.coords)" class="btn btn-ghost btn-sm vrg-state-copy-btn" :title="$t('http.app.copy_coords')"><icon name="copy" :size="16"></icon></button>
                </div>
                <div v-if="lbsLocation" class="vrg-state-location-row">
                  <a :href="lbsLocation.url" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">{{ lbsLocation.label }}</a>
                  <button @click="copyToClipboard(lbsLocation.coords)" class="btn btn-ghost btn-sm vrg-state-copy-btn" :title="$t('http.app.copy_coords')"><icon name="copy" :size="16"></icon></button>
                </div>
              </div>
              <div style="display: flex; gap: var(--spacing-sm); flex-wrap: wrap; margin-top: var(--spacing-xs);">
                <button class="btn btn-outline btn-sm" @click="takePhoto(null)" :disabled="takingPhoto">
                  {{ takingPhoto ? $t('http.app.taking_photo') : $t('http.app.take_photo') }}
                </button>
                <button class="btn btn-outline btn-sm" @click="takePhoto('night')" :disabled="takingPhoto">
                  {{ takingPhoto ? $t('http.app.taking_photo') : $t('http.app.take_photo_night') }}
                </button>
                <button class="btn btn-outline btn-sm" @click="takeShortVideo()" :disabled="takingShortVideo">
                  {{ takingShortVideo ? $t('http.app.taking_photo') : $t('http.app.take_short_video') }}
                </button>
              </div>
            </div>
          </div>
          <template v-if="takenPhotos.length > 0">
            <div>
              <div style="font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text-secondary); margin-bottom: var(--spacing-xs);">{{ $t('http.app.taken_photos') }}</div>
              <div style="display: flex; flex-wrap: wrap; gap: var(--spacing-sm);">
                <div v-for="item in takenPhotos" :key="item.filename" style="width: 100px; height: 75px; flex-shrink: 0;">
                  <trips-media-item :item="item" :initial-video-ready="true"></trips-media-item>
                </div>
              </div>
            </div>
          </template>
          <template v-if="takenShortVideos.length > 0">
            <div>
              <div style="font-size: var(--font-size-sm); font-weight: 600; color: var(--color-text-secondary); margin-bottom: var(--spacing-xs);">{{ $t('http.app.taken_videos') }}</div>
              <div style="display: flex; flex-wrap: wrap; gap: var(--spacing-sm);">
                <div v-for="item in takenShortVideos" :key="item.filename" style="width: 100px; height: 75px; flex-shrink: 0;">
                  <trips-media-item :item="item" :initial-video-ready="true"></trips-media-item>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- Trip block -->
        <div v-if="loading" class="dashboard-tile">
          <div class="dashboard-tile-header">
            <shimmer height="20px" width="20px" style="border-radius: 4px; flex-shrink: 0;"></shimmer>
            <shimmer height="15px" width="55%"></shimmer>
          </div>
          <shimmer height="14px" width="80%"></shimmer>
          <shimmer height="12px" width="55%"></shimmer>
        </div>
        <div v-else class="dashboard-tile" :class="trip && trip.state ? 'dashboard-tile--' + trip.state : ''" @click="$emit('navigate', 'trips')">
          <div class="dashboard-tile-header">
            <span class="dashboard-tile-icon"><icon name="gps_tracks" :size="20"></icon></span>
            <span class="dashboard-tile-title">{{ $t('http.home.trip_title') }}</span>
          </div>
          <template v-if="trip && trip.state">
            <div class="dashboard-tile-row">{{ tripDurationLabel }}</div>
            <div class="dashboard-tile-meta">{{ $t('http.trips.time_from', {time: tripStartLabel}) }}</div>
          </template>
          <div v-else class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
        </div>

      </div>

      <!-- Row 2: status tiles -->
      <div class="dashboard-tiles">

        <!-- System -->
        <div v-if="loading" class="dashboard-tile">
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

        <!-- WiFi -->
        <div v-if="loading" class="dashboard-tile">
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
              <span>{{ wifiType ? $t('http.home.connected') : $t('http.home.disconnected') }}</span>
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

        <!-- Modem -->
        <div v-if="loading" class="dashboard-tile">
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
            <span class="dashboard-tile-icon"><icon :name="modem && modem.connected ? 'modem' : 'modem_off'" :size="20"></icon></span>
            <span class="dashboard-tile-title">{{ $t('http.settings.modem') }}</span>
            <span class="status-indicator" style="margin-left: auto;">
              <span class="status-dot" :class="{ active: !!(modem && modem.connected) }"></span>
              <span>{{ modem && modem.connected ? $t('http.home.enabled') : $t('http.home.disabled') }}</span>
            </span>
          </div>
          <template v-if="modem && modem.connected">
            <div v-if="modem.model" class="dashboard-tile-row">
              <span class="dashboard-tile-label">{{ $t('http.home.model_label') }}</span>
              <span>{{ modem.model }}</span>
            </div>
            <div v-if="modem.operator" class="dashboard-tile-row">
              <span class="dashboard-tile-label">Operator:</span>
              <span>{{ modem.operator }}<template v-if="modem.access_tech"> · {{ modem.access_tech }}</template></span>
            </div>
            <div v-if="connections && connections.modem && connections.modem.ip" class="dashboard-tile-row">
              <span class="dashboard-tile-label">IP</span>
              <span>{{ connections.modem.ip }}</span>
            </div>
          </template>
        </div>

        <!-- WireGuard -->
        <div v-if="loading" class="dashboard-tile">
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
              <span class="status-dot" :class="{ active: !!(wireguard && wireguard.active) }"></span>
              <span>{{ wireguard && wireguard.active ? $t('http.home.wg_active') : $t('http.home.wg_inactive') }}</span>
            </span>
          </div>
          <template v-if="wireguard && wireguard.active">
            <div v-if="wireguard.ip_address" class="dashboard-tile-row">
              <span class="dashboard-tile-label">IP</span>
              <span>{{ wireguard.ip_address }}</span>
            </div>
          </template>
        </div>

        <!-- Power -->
        <div v-if="loading" class="dashboard-tile">
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
            <span class="dashboard-tile-title">{{ $t('http.settings.power') }}</span>
            <span v-if="power !== null" class="status-indicator" style="margin-left: auto;">
              <span class="status-dot" :class="{ active: power.charging }"></span>
              <span>{{ power.charging ? $t('http.home.charging') : $t('http.home.on_battery') }}</span>
            </span>
          </div>
          <template v-if="power !== null">
            <div v-if="power.source" class="dashboard-tile-row">
              <span class="dashboard-tile-label">{{ $t('http.home.type_label') }}</span>
              <span>{{ power.source.title }}</span>
            </div>
            <div v-if="power.source && power.source.battery_telemetry" class="dashboard-tile-row">
              <span class="dashboard-tile-label">{{ $t('http.home.charge_label') }}</span>
              <strong>{{ power.battery_percent }}%</strong>
            </div>
            <div v-if="power.uptime != null" class="dashboard-tile-row">
              <span class="dashboard-tile-label">{{ $t('http.power.uptime_label') }}</span>
              <span>{{ uptimeLabel }}</span>
            </div>
          </template>
          <div v-else class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
        </div>

        <!-- Camera -->
        <div v-if="loading" class="dashboard-tile">
          <div class="dashboard-tile-header">
            <shimmer height="20px" width="20px" style="border-radius: 4px; flex-shrink: 0;"></shimmer>
            <shimmer height="15px" width="45%"></shimmer>
          </div>
          <shimmer height="13px" width="65%"></shimmer>
        </div>
        <div v-else class="dashboard-tile" @click="$emit('navigate', 'camera')">
          <div class="dashboard-tile-header">
            <span class="dashboard-tile-icon"><icon name="camera" :size="20"></icon></span>
            <span class="dashboard-tile-title">{{ $t('http.settings.camera') }}</span>
            <span v-if="camera !== null" class="status-indicator" style="margin-left: auto;">
              <span class="status-dot" :class="{ active: camera.video_state === 'record' }"></span>
              <span>{{ cameraStateLabel }}</span>
            </span>
          </div>
          <template v-if="camera !== null">
            <div class="dashboard-tile-row">
              <span class="dashboard-tile-label">{{ $t('http.home.model_label') }}</span>
              <span>{{ camera.model || $t('http.home.camera_no_found_short') }}</span>
            </div>
            <div class="dashboard-tile-row">
              <span class="dashboard-tile-label">{{ $t('http.home.thermal_label') }}</span>
              <span>{{ thermalStatusLabel }}</span>
            </div>
          </template>
          <div v-else class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
        </div>

      </div>
    </div>
  `,

  data() {
    return {
      connections: null,
      modem: null,
      wireguard: null,
      trip: null,
      location: null,
      system: null,
      error: '',
      loading: true,
      takingPhoto: false,
      takenPhotos: [],
      takingShortVideo: false,
      takenShortVideos: [],
    };
  },

  computed: {
    camera() {
      return this.appStatusData?.camera || null;
    },

    power() {
      return this.appStatusData?.power || null;
    },

    cameraStateLabel() {
      const camera = this.appStatusData?.camera;
      if (!camera) return '—';
      const labels = {
        record: this.$t('http.camera.state_record'),
        pause: this.$t('http.camera.state_pause'),
        stop: this.$t('http.camera.state_stop'),
      };
      return labels[camera.video_state] || '—';
    },

    thermalStatusLabel() {
      const status = this.appStatusData?.camera?.thermal_status;
      const labels = {
        normal: this.$t('http.camera.thermal_normal'),
        downscaled: this.$t('http.camera.thermal_downscaled'),
        overheated: this.$t('http.camera.thermal_overheated'),
      };
      return labels[status] || '—';
    },

    powerIcon() {
      const power = this.appStatusData?.power;
      if (!power) return 'battery';
      if (!power?.source?.battery_telemetry) return 'power_plug';
      return power.charging ? 'battery_charging' : 'battery';
    },

    wifiIcon() {
      return (this.connections?.wifi?.enabled || this.connections?.ap?.enabled) ? 'wifi' : 'wifi_off';
    },

    wifiSsid() {
      return this.connections?.wifi?.ssid || this.connections?.ap?.ssid || null;
    },

    wifiType() {
      if (!this.connections?.ap?.enabled && !this.connections?.wifi?.enabled) return null;
      return (this.connections?.ap?.enabled && !this.connections?.wifi?.enabled) ? 'Access Point' : 'Client';
    },

    wifiIp() {
      return this.connections?.wifi?.ip || this.connections?.ap?.ip || null;
    },

    statusLastMediaItem() {
      const item = this.appStatusData?.last_media?.item;
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

    statusLastMediaReady() {
      return this.appStatusData?.last_media?.item?.ready === true;
    },

    gpsLocation() {
      const gps = this.location?.gps;
      const lat = parseFloat(gps?.latitude);
      const lng = parseFloat(gps?.longitude);
      if (!isFinite(lat) || !isFinite(lng)) return null;
      return {
        url: `https://yandex.ru/maps/?mode=search&text=${lat}%2C${lng}`,
        label: `GPS: ${lat.toFixed(2)}, ${lng.toFixed(2)}`,
        coords: `${lat}, ${lng}`,
      };
    },

    lbsLocation() {
      const lbs = this.location?.lbs;
      const lat = parseFloat(lbs?.latitude);
      const lng = parseFloat(lbs?.longitude);
      if (!isFinite(lat) || !isFinite(lng)) return null;
      return {
        url: `https://yandex.ru/maps/?mode=search&text=${lat}%2C${lng}`,
        label: `LBS: ${lat.toFixed(2)}, ${lng.toFixed(2)}`,
        coords: `${lat}, ${lng}`,
      };
    },

    statusLastUpdatedLabel() {
      if (!this.appStatusLastUpdated) return null;
      return this.appStatusLastUpdated.toLocaleTimeString(VrgI18n.locale, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    },

    tripDurationLabel() {
      if (!this.trip?.state || !this.trip?.start) return '';
      const prefix = this.trip.state === 'in_trip' ? this.$t('http.home.trip_in_progress') : this.$t('http.home.trip_parked');
      const duration = this._formatDuration(this.trip.start);
      return prefix + ': ' + duration;
    },

    tripStartLabel() {
      if (!this.trip?.start) return '';
      const d = new Date(this.trip.start);
      return d.toLocaleTimeString(VrgI18n.locale, { hour: '2-digit', minute: '2-digit' }) + ' ' + d.toLocaleDateString(VrgI18n.locale, { day: 'numeric', month: 'long' });
    },

    uptimeLabel() {
      const sec = this.appStatusData?.power?.uptime;
      if (sec == null) return '—';
      const h = Math.floor(sec / 3600);
      const m = Math.floor(sec / 60) % 60;
      if (h > 0) return m > 0 ? this.$t('http.trips.duration_h_m', { h, m }) : this.$t('http.trips.duration_h', { h });
      return this.$t('http.trips.duration_min', { m: Math.max(m, 1) });
    },

    cpuTempLabel() {
      const temp = this.system?.cpu_temp;
      if (temp == null) return '—';
      return temp + ' °C';
    },
  },

  methods: {
    _formatDuration(startIso) {
      const start = new Date(startIso);
      const diffMs = Date.now() - start;
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return this.$t('http.trips.less_than_min');
      if (diffMin < 60) return this.$t('http.trips.duration_min', { m: diffMin });
      const h = Math.floor(diffMin / 60);
      const m = diffMin % 60;
      return m > 0 ? this.$t('http.trips.duration_h_m', { h, m }) : this.$t('http.trips.duration_h', { h });
    },

    _nameToDatetime(name) {
      const [date, time] = name.split('_');
      return date + 'T' + time.replace(/-/g, ':');
    },

    async copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text);
      } catch (e) {
        // fallback for non-secure context
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
      }
    },

    async takePhoto(mode) {
      if (this.takingPhoto) return;
      this.takingPhoto = true;
      try {
        const body = mode ? { mode } : {};
        const response = await fetch('/api/camera/photo', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await response.json();
        if (!response.ok) return;
        const datetime = this._nameToDatetime(data.name);
        this.takenPhotos = [{ type: 'photo', filename: data.name + '.jpg', date: datetime }, ...this.takenPhotos];
      } catch (err) {
        console.warn('Photo capture error', err);
      } finally {
        this.takingPhoto = false;
      }
    },

    async takeShortVideo() {
      if (this.takingShortVideo) return;
      this.takingShortVideo = true;
      try {
        const response = await fetch('/api/camera/short_video', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        });
        const data = await response.json();
        if (!response.ok) return;
        const datetime = this._nameToDatetime(data.name);
        this.takenShortVideos = [{ type: 'video', filename: data.name + '.mp4', date: datetime }, ...this.takenShortVideos];
      } catch (err) {
        console.warn('Short video capture error', err);
      } finally {
        this.takingShortVideo = false;
      }
    },

    async load() {
      this.loading = true;
      this.error = '';
      try {
        const response = await fetch('/api/dashboard/status', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('http.home.error_load');
        } else {
          this.connections = data.connections;
          this.modem = data.modem;
          this.wireguard = data.wireguard;
          this.trip = data.trip || null;
          this.location = data.location || null;
          this.system = data.system || null;
        }
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    },

  },

  async mounted() {
    await this.load();
  },
};

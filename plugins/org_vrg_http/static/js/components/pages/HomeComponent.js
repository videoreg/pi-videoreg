// Компонент главной страницы с дашбордом
const HomeComponent = {
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <h1 class="page-title">{{ $t('http.home.title') }}</h1>
      </div>

      <div v-if="loading" class="alert alert-info">{{ $t('http.home.loading') }}</div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div class="dashboard-tiles">

        <!-- WiFi / AP -->
        <div class="dashboard-tile" @click="$emit('navigate', 'wifi')">
          <div class="dashboard-tile-header">
            <span class="dashboard-tile-icon">📶</span>
            <span class="dashboard-tile-title">WiFi / AP</span>
          </div>
          <template v-if="connections">
            <div class="dashboard-tile-row">
              <span class="dashboard-tile-label">WiFi</span>
              <span class="status-indicator" style="padding: 3px 8px;">
                <span class="status-dot" :class="{ active: connections.wifi && connections.wifi.enabled }"></span>
                <span>{{ connections.wifi && connections.wifi.enabled ? (connections.wifi.ssid || $t('http.home.wifi_connected')) : $t('http.home.off') }}</span>
              </span>
            </div>
            <div class="dashboard-tile-row">
              <span class="dashboard-tile-label">AP</span>
              <span class="status-indicator" style="padding: 3px 8px;">
                <span class="status-dot" :class="{ active: connections.ap && connections.ap.enabled }"></span>
                <span>{{ connections.ap && connections.ap.enabled ? (connections.ap.ssid || $t('http.home.ap_active')) : $t('http.home.off') }}</span>
              </span>
            </div>
            <div v-if="connections.wifi && connections.wifi.ip" class="dashboard-tile-meta">IP: {{ connections.wifi.ip }}</div>
            <div v-else-if="connections.ap && connections.ap.ip" class="dashboard-tile-meta">IP: {{ connections.ap.ip }}</div>
          </template>
          <div v-else-if="!loading" class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
        </div>

        <!-- Модем -->
        <div class="dashboard-tile" @click="$emit('navigate', 'modem')">
          <div class="dashboard-tile-header">
            <span class="dashboard-tile-icon">📡</span>
            <span class="dashboard-tile-title">{{ $t('http.settings.modem') }}</span>
          </div>
          <template v-if="connections && connections.modem">
            <div class="dashboard-tile-row">
              <span class="dashboard-tile-label">{{ $t('http.home.connection_label') }}</span>
              <span class="status-indicator" style="padding: 3px 8px;">
                <span class="status-dot" :class="{ active: connections.modem.enabled }"></span>
                <span>{{ connections.modem.enabled ? $t('http.home.modem_active') : $t('http.home.off') }}</span>
              </span>
            </div>
            <div v-if="modem" class="dashboard-tile-row">
              <span class="dashboard-tile-label">{{ $t('http.home.signal_label') }}</span>
              <span :style="{ color: signalColor }">{{ modem.signal_quality }}%</span>
            </div>
            <div v-if="modem && modem.operator" class="dashboard-tile-meta">{{ modem.operator }} · {{ modem.access_tech }}</div>
            <div v-else-if="connections.modem.ip" class="dashboard-tile-meta">IP: {{ connections.modem.ip }}</div>
          </template>
          <div v-else-if="!loading" class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
        </div>

        <!-- WireGuard -->
        <div class="dashboard-tile" @click="$emit('navigate', 'wireguard')">
          <div class="dashboard-tile-header">
            <span class="dashboard-tile-icon">🔐</span>
            <span class="dashboard-tile-title">WireGuard</span>
          </div>
          <template v-if="wireguard !== null">
            <div class="dashboard-tile-row">
              <span class="dashboard-tile-label">{{ $t('http.home.interface_label') }}</span>
              <span class="status-indicator" style="padding: 3px 8px;">
                <span class="status-dot" :class="{ active: wireguard.active }"></span>
                <span>{{ wireguard.active ? $t('http.home.wg_active') : $t('http.home.wg_inactive') }}</span>
              </span>
            </div>
            <div v-if="wireguard.ip_address" class="dashboard-tile-meta">IP: {{ wireguard.ip_address }}</div>
          </template>
          <div v-else-if="!loading" class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
        </div>

        <!-- Камера -->
        <div class="dashboard-tile" @click="$emit('navigate', 'camera')">
          <div class="dashboard-tile-header">
            <span class="dashboard-tile-icon">📷</span>
            <span class="dashboard-tile-title">{{ $t('http.settings.camera') }}</span>
          </div>
          <template v-if="camera !== null">
            <div class="dashboard-tile-row">
              <span class="dashboard-tile-label">{{ $t('http.home.record_label') }}</span>
              <span class="status-indicator" style="padding: 3px 8px;">
                <span class="status-dot" :class="{ active: camera.video_state === 'record' }"></span>
                <span>{{ cameraStateLabel }}</span>
              </span>
            </div>
            <div v-if="camera.model" class="dashboard-tile-meta">{{ camera.model }}</div>
            <div v-else class="dashboard-tile-meta">{{ $t('http.home.camera_no_found') }}</div>
          </template>
          <div v-else-if="!loading" class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
        </div>

        <!-- Питание -->
        <div class="dashboard-tile" @click="$emit('navigate', 'power')">
          <div class="dashboard-tile-header">
            <span class="dashboard-tile-icon">🔋</span>
            <span class="dashboard-tile-title">{{ $t('http.settings.power') }}</span>
          </div>
          <template v-if="power !== null">
            <template v-if="power.source && power.source.battery_telemetry">
              <div class="dashboard-tile-row">
                <span class="dashboard-tile-label">{{ $t('http.home.charge_label') }}</span>
                <strong>{{ power.battery_percent }}%</strong>
              </div>
              <div class="dashboard-tile-row">
                <span class="dashboard-tile-label">{{ $t('http.home.power_label') }}</span>
                <span class="status-indicator" style="padding: 3px 8px;">
                  <span class="status-dot" :class="{ active: power.charging }"></span>
                  <span>{{ power.charging ? $t('http.home.charging') : $t('http.home.on_battery') }}</span>
                </span>
              </div>
            </template>
            <template v-else>
              <div v-if="power.source" class="dashboard-tile-meta">{{ power.source.title }}</div>
            </template>
          </template>
          <div v-else-if="!loading" class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
        </div>

        <!-- Хранилище -->
        <div v-if="false" class="dashboard-tile" @click="$emit('navigate', 'storage')">
          <div class="dashboard-tile-header">
            <span class="dashboard-tile-icon">💾</span>
            <span class="dashboard-tile-title">{{ $t('http.settings.storage') }}</span>
          </div>
          <template v-if="storage !== null">
            <div class="dashboard-tile-row">
              <span class="dashboard-tile-label">{{ $t('http.home.data_label') }}</span>
              <strong :style="{ color: storageColor }">{{ storage.data_use_percent }}%</strong>
            </div>
            <div class="dashboard-tile-meta">{{ $t('http.home.storage_fill') }}</div>
          </template>
          <div v-else-if="!loading" class="dashboard-tile-meta">{{ $t('http.home.no_data') }}</div>
        </div>

      </div>
    </div>
  `,

  data() {
    return {
      connections: null,
      modem: null,
      wireguard: null,
      camera: null,
      power: null,
      storage: null,
      error: '',
      loading: false
    };
  },

  computed: {
    signalColor() {
      if (!this.modem) return 'var(--color-text-secondary)';
      const q = this.modem.signal_quality;
      if (q >= 70) return 'var(--color-success)';
      if (q >= 40) return 'var(--color-warning)';
      return 'var(--color-error)';
    },

    cameraStateLabel() {
      if (!this.camera) return '—';
      const labels = {
        record: this.$t('http.camera.state_record'),
        pause: this.$t('http.camera.state_pause'),
        stop: this.$t('http.camera.state_stop')
      };
      return labels[this.camera.video_state] || '—';
    },

    storageColor() {
      if (!this.storage) return 'var(--color-text-secondary)';
      const p = this.storage.data_use_percent;
      if (p >= 90) return 'var(--color-error)';
      if (p >= 70) return 'var(--color-warning)';
      return 'var(--color-success)';
    }
  },

  methods: {
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
          this.camera = data.camera;
          this.power = data.power || null;
          this.storage = data.storage || null;
        }
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    }
  },

  async mounted() {
    await this.load();
  }
};

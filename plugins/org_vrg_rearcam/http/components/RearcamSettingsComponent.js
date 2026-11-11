// Rear cameras settings page: pair WiFi rear-view cameras over BLE, list them, forget.
const RearcamSettingsComponent = {
  components: { Icon },
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('rearcam.settings.title') }}</h1>
        <div v-if="loading" class="spinner spinner-sm"></div>
        <button v-else class="btn btn-icon" @click="loadDevices" :title="$t('http.common.refresh')">↻</button>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="success" class="alert alert-success">{{ success }}</div>

      <!-- Paired cameras -->
      <div class="info-block">
        <div class="section-title">{{ $t('rearcam.settings.paired_title') }}</div>
        <p style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary);">
          {{ $t('rearcam.settings.hint') }}
        </p>

        <div v-if="devices.length === 0" style="color: var(--color-text-secondary);">
          {{ $t('rearcam.settings.no_cameras') }}
        </div>

        <div
          v-for="dev in devices"
          :key="dev.device_id"
          class="info-rows"
          style="margin-bottom: var(--spacing-md);"
        >
          <div class="info-row">
            <span class="info-label">{{ dev.name || $t('rearcam.settings.camera_n', { n: dev.number }) }}</span>
            <span class="status-indicator" style="padding: 3px 8px;">
              <span class="status-dot" :class="{ active: dev.online }"></span>
              <span>{{ dev.online ? $t('rearcam.settings.online') : $t('rearcam.settings.offline') }}</span>
            </span>
          </div>
          <div class="info-row">
            <span class="info-label">#{{ dev.number }}</span>
            <span>
              <code style="background: var(--color-bg-tertiary); padding: 2px 6px; border-radius: var(--radius-sm);">{{ dev.device_id }}</code>
              <span v-if="dev.ip"> · {{ dev.ip }}</span>
              <span v-if="dev.firmware"> · fw {{ dev.firmware }}</span>
            </span>
          </div>
          <div class="info-row">
            <span></span>
            <button class="btn btn-ghost-danger" @click="forget(dev)" :disabled="busy">
              {{ $t('rearcam.settings.forget_btn') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Add a camera -->
      <div class="info-block">
        <div class="section-title">{{ $t('rearcam.settings.add_btn') }}</div>
        <p style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary);">
          {{ $t('rearcam.settings.scan_hint') }}
        </p>

        <div v-if="!provisioningMac">
          <button class="btn btn-primary" @click="scan" :disabled="scanning || busy">
            {{ scanning ? $t('rearcam.settings.scanning') : $t('rearcam.settings.scan_btn') }}
          </button>

          <div v-if="scanned && !scanning && found.length === 0" style="margin-top: var(--spacing-md); color: var(--color-text-secondary);">
            {{ $t('rearcam.settings.no_devices') }}
          </div>

          <div style="margin-top: var(--spacing-md);">
            <div
              v-for="dev in found"
              :key="dev.mac"
              class="info-block"
              style="display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md); margin-bottom: var(--spacing-sm);"
            >
              <div>
                <div class="section-title" style="margin-bottom: 4px;">{{ dev.name }}</div>
                <p style="margin: 0; color: var(--color-text-secondary);">
                  <code style="background: var(--color-bg-tertiary); padding: 2px 6px; border-radius: var(--radius-sm);">{{ dev.mac }}</code>
                  <span v-if="dev.rssi != null"> · {{ dev.rssi }} dBm</span>
                </p>
              </div>
              <button class="btn btn-ghost" @click="provision(dev)" :disabled="busy">
                {{ $t('rearcam.settings.connect_btn') }}
              </button>
            </div>
          </div>
        </div>

        <div v-else style="display: flex; align-items: center; gap: var(--spacing-md);">
          <div class="spinner spinner-sm"></div>
          <span>{{ $t('rearcam.settings.provisioning') }}</span>
        </div>
      </div>
    </div>
  `,

  data() {
    return {
      devices: [],
      found: [],
      loading: false,
      scanning: false,
      scanned: false,
      busy: false,
      provisioningMac: null,
      error: '',
      success: '',
    };
  },

  methods: {
    provisionErrorText(err) {
      const key = {
        bad_password: 'rearcam.settings.error_bad_password',
        ssid_not_found: 'rearcam.settings.error_ssid_not_found',
        timeout: 'rearcam.settings.error_timeout',
      }[err];
      return key ? this.$t(key) : (this.$t('rearcam.settings.error_provision') + (err ? `: ${err}` : ''));
    },

    async loadDevices() {
      this.error = '';
      this.loading = true;
      try {
        const response = await fetch('/api/rearcam/devices', { credentials: 'same-origin' });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('rearcam.settings.error_load');
          return;
        }
        this.devices = result.devices || [];
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    },

    async scan() {
      this.error = '';
      this.success = '';
      this.scanning = true;
      this.scanned = false;
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 25000);
        const response = await fetch('/api/rearcam/scan', {
          credentials: 'same-origin',
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('rearcam.settings.error_scan');
          return;
        }
        const paired = new Set(this.devices.map(d => (d.ble_mac || '').toUpperCase()));
        this.found = (result.devices || []).filter(d => !paired.has((d.mac || '').toUpperCase()));
        this.scanned = true;
      } catch (err) {
        this.error = err.name === 'AbortError'
          ? this.$t('rearcam.settings.error_timeout')
          : this.$t('http.common.error_connection');
      } finally {
        this.scanning = false;
      }
    },

    async provision(dev) {
      this.error = '';
      this.success = '';
      this.busy = true;
      this.provisioningMac = dev.mac;
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 100000);
        const response = await fetch('/api/rearcam/provision', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mac: dev.mac, name: dev.name || '' }),
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        const result = await response.json();
        if (!response.ok) {
          this.error = this.provisionErrorText(result.error || '');
          return;
        }
        this.success = this.$t('rearcam.settings.provisioned');
        this.found = [];
        this.scanned = false;
        await this.loadDevices();
      } catch (err) {
        this.error = err.name === 'AbortError'
          ? this.$t('rearcam.settings.error_timeout')
          : this.$t('http.common.error_connection');
      } finally {
        this.busy = false;
        this.provisioningMac = null;
      }
    },

    async forget(dev) {
      if (!confirm(this.$t('rearcam.settings.forget_confirm'))) return;
      this.error = '';
      this.success = '';
      this.busy = true;
      try {
        const response = await fetch('/api/rearcam/forget', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ number: dev.number })
        });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('rearcam.settings.error_load');
          return;
        }
        this.devices = result.devices || [];
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.busy = false;
      }
    },
  },

  async mounted() {
    await this.loadDevices();
  }
};

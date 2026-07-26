// Компонент страницы питания (PiSugar UPS)
const PowerSettingsComponent = {
  components: { TabSwitch, ProgressBar, Icon, ToggleSwitch },
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('power.power.title') }}</h1>
        <div v-if="statusLoading" class="spinner spinner-sm"></div>
        <button v-else class="btn btn-icon" @click="loadStatus" :disabled="statusLoading" :title="$t('http.common.refresh')">↻</button>
      </div>

      <tab-switch
        v-if="status !== null && capabilities !== null"
        v-model="activeTab"
        :tabs="tabs"
        style="margin-bottom: var(--spacing-lg);"></tab-switch>

      <!-- Вкладка: Статус -->
      <div v-show="activeTab === 'status'">
        <div v-if="statusError" class="alert alert-error">{{ statusError }}</div>
        <div v-if="actionError" class="alert alert-error">{{ actionError }}</div>

        <div v-if="status !== null" class="info-block">
          <div class="section-title">{{ $t('power.power.battery_title') }}</div>

          <div class="info-rows">
            <!-- Источник питания -->
            <div class="info-row">
              <span class="info-label">{{ $t('power.power.power_source') }}</span>
              <strong>{{ capabilities ? capabilities.title : '—' }}</strong>
            </div>

            <!-- Заряд батареи -->
            <div v-if="!capabilities || capabilities.battery_telemetry" class="info-row">
              <span class="info-label">{{ $t('power.power.battery_precent') }}</span>
              <progress-bar
                :value="status ? status.battery_percent : 0"
                :variant="batteryVariant(status ? status.battery_percent : 0)"
                :show-label="true"
                style="width: 160px;"
              ></progress-bar>
            </div>

            <!-- Статус зарядки -->
            <div class="info-row">
              <span class="info-label">{{ $t('power.power.charging_label') }}</span>
              <span class="status-indicator" style="padding: 3px 8px;">
                <span class="status-dot" :class="{ active: status && status.charging }"></span>
                <span>{{ status ? (status.charging ? $t('power.power.charging') : $t('power.power.on_battery')) : '—' }}</span>
              </span>
            </div>

            <!-- Температура PiSugar -->
            <div v-if="status && status.temp != null" class="info-row">
              <span class="info-label">{{ $t('power.power.temp_label') }}</span>
              <strong>{{ status.temp + ' °C' }}</strong>
            </div>

            <!-- Время работы -->
            <div class="info-row">
              <span class="info-label">{{ $t('power.power.uptime_label') }}</span>
              <strong>{{ uptimeLabel }}</strong>
            </div>

            <!-- Режим пробуждения -->
            <div class="info-row">
              <span class="info-label">{{ $t('power.power.wakeup_label') }}</span>
              <strong>{{ wakeupLabel }}</strong>
            </div>

            <!-- Keep alive -->
            <div class="info-row">
              <span class="info-label">{{ $t('power.power.keep_alive_label') }}</span>
              <strong>{{ keepAliveLabel }}</strong>
            </div>
          </div>
        </div>

        <div style="display: flex; gap: var(--spacing-sm); margin-top: var(--spacing-lg);">
          <button class="btn btn-ghost" @click="powerKeepAlive" :disabled="actionLoading">
            {{ actionLoading === 'keep_alive' ? $t('power.power.keep_alive_wait') : keepAliveSuccess ? $t('common.success') : $t('power.power.keep_alive_btn') }}
          </button>
          <button class="btn btn-ghost" @click="powerReboot" :disabled="actionLoading">
            {{ actionLoading === 'reboot' ? $t('power.power.rebooting') : $t('power.power.reboot_btn') }}
          </button>
          <button class="btn btn-ghost-danger" @click="powerShutdown" :disabled="actionLoading">
            {{ actionLoading === 'shutdown' ? $t('power.power.shutting_down') : $t('power.power.shutdown_btn') }}
          </button>
        </div>

      </div>

      <!-- Вкладка: Настройки -->
      <div v-show="activeTab === 'settings'">
        <div v-if="settingsError" class="alert alert-error">{{ settingsError }}</div>
        <div v-if="settingsSuccess" class="alert alert-success">{{ settingsSuccess }}</div>

        <div v-if="capabilities && capabilities.charging_protection" class="info-block">
          <div class="section-title">{{ $t('power.power.charging_protection_label') }}</div>
          <p style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary);">
            {{ $t('power.power.charging_protection_hint') }}
          </p>
          <toggle-switch
            v-model="chargingProtection"
            :disabled="chargingProtectionLoading"
            @update:modelValue="onChargingProtectionToggle"
          ></toggle-switch>
        </div>

        <div v-if="selectedWakeup !== null" class="info-block">
          <div class="section-title">{{ $t('power.power.wakeup_label') }}</div>
          <p v-if="capabilities && capabilities.alarm_wakeup" style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary);">
            {{ $t('power.power.wakeup_description') }}
          </p>
          <p v-else style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary);">
            {{ $t('power.power.wakeup_not_supported', { source: capabilities ? capabilities.title : '' }) }}
          </p>

          <div style="max-width: 400px;">
            <div style="margin-bottom: var(--spacing-md);">
              <label style="display: block; margin-bottom: var(--spacing-sm); color: var(--color-text-secondary); font-size: 0.875rem;">
                {{ $t('power.power.wakeup_mode_label') }}
              </label>
              <select
                v-model="selectedWakeup"
                class="form-input"
                :disabled="saving || (capabilities && !capabilities.alarm_wakeup)"
              >
                <option
                  v-for="opt in wakeupOptions"
                  :key="opt.value"
                  :value="opt.value"
                >{{ opt.label }}</option>
              </select>
            </div>

            <button
              class="btn btn-primary"
              @click="saveWakeup"
              :disabled="saving || settingsLoading || (capabilities && !capabilities.alarm_wakeup)"
            >
              {{ saving ? $t('common.saving') : $t('common.save') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Вкладка: Маяк (BLE) -->
      <div v-show="activeTab === 'beacon'">
        <div v-if="bleError" class="alert alert-error">{{ bleError }}</div>

        <div v-if="ble.supported === false" class="alert alert-error">
          {{ $t('power.power.ble_unsupported') }}
        </div>

        <template v-else>
          <div class="info-block">
            <div class="section-title">{{ $t('power.power.ble_title') }}</div>
            <p style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary);">
              {{ $t('power.power.ble_hint') }}
            </p>
            <div style="display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md);">
              <span>{{ $t('power.power.ble_enable_label') }}</span>
              <toggle-switch
                v-model="ble.enabled"
                :disabled="bleBusy"
                @update:modelValue="onBleToggle"
              ></toggle-switch>
            </div>

            <div style="margin-top: var(--spacing-lg);">
              <label style="display: block; margin-bottom: var(--spacing-sm); color: var(--color-text-secondary); font-size: 0.875rem;">
                {{ $t('power.power.ble_grace_label') }}
              </label>
              <p style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary); font-size: 0.875rem;">
                {{ $t('power.power.ble_grace_hint') }}
              </p>
              <div style="display: flex; align-items: center; gap: var(--spacing-sm); max-width: 320px;">
                <input
                  type="number"
                  class="form-input"
                  v-model.number="bleGraceMinutes"
                  :min="1"
                  :max="120"
                  :disabled="bleGraceSaving"
                  style="width: 100px;"
                />
                <span style="color: var(--color-text-secondary);">{{ $t('power.power.ble_grace_unit') }}</span>
                <button class="btn btn-primary" @click="saveBleGrace" :disabled="bleGraceSaving">
                  {{ bleGraceSaving ? $t('common.saving') : $t('common.save') }}
                </button>
              </div>
            </div>
          </div>

          <!-- Выбранный маяк -->
          <div v-if="ble.target" class="info-block">
            <div class="section-title">{{ $t('power.power.ble_target_label') }}</div>
            <div class="info-rows">
              <div class="info-row">
                <span class="info-label">{{ ble.target.name || $t('power.power.ble_unnamed') }}</span>
                <code style="background: var(--color-bg-tertiary); padding: 2px 6px; border-radius: var(--radius-sm);">{{ ble.target.mac }}</code>
              </div>
              <div v-if="ble.enabled" class="info-row">
                <span class="info-label">{{ $t('power.power.ble_status_label') }}</span>
                <span class="status-indicator" style="padding: 3px 8px;">
                  <span class="status-dot" :class="{ active: ble.present }"></span>
                  <span>{{ ble.present ? $t('power.power.ble_present') : $t('power.power.ble_absent') }}</span>
                </span>
              </div>
            </div>
            <button class="btn btn-ghost" style="margin-top: var(--spacing-md);" @click="changeBeacon" :disabled="bleBusy">
              {{ $t('power.power.ble_change') }}
            </button>
            <p style="margin-top: var(--spacing-md); color: var(--color-text-secondary); font-size: 0.875rem;">
              {{ $t('power.power.ble_wakeup_hint') }}
            </p>
          </div>

          <!-- Сканирование и выбор устройства -->
          <div v-else class="info-block">
            <div class="section-title">{{ $t('power.power.ble_select_title') }}</div>
            <p style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary);">
              {{ $t('power.power.ble_select_hint') }}
            </p>
            <button class="btn btn-primary" @click="scanBle" :disabled="bleScanning">
              {{ bleScanning ? $t('power.power.ble_scanning') : $t('power.power.ble_scan_btn') }}
            </button>

            <div v-if="bleScanned && !bleScanning && bleDevices.length === 0" style="margin-top: var(--spacing-md); color: var(--color-text-secondary);">
              {{ $t('power.power.ble_no_devices') }}
            </div>

            <div style="margin-top: var(--spacing-md);">
              <div
                v-for="dev in bleDevices"
                :key="dev.mac"
                class="info-block"
                style="display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md); margin-bottom: var(--spacing-sm);"
              >
                <div>
                  <div class="section-title" style="margin-bottom: 4px;">{{ dev.name || $t('power.power.ble_unnamed') }}</div>
                  <p style="margin: 0; color: var(--color-text-secondary);">
                    <code style="background: var(--color-bg-tertiary); padding: 2px 6px; border-radius: var(--radius-sm);">{{ dev.mac }}</code>
                    <span v-if="dev.rssi != null"> · {{ dev.rssi }} dBm</span>
                  </p>
                </div>
                <button class="btn btn-ghost" @click="selectBeacon(dev)" :disabled="bleBusy">
                  {{ $t('power.power.ble_select') }}
                </button>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
  `,

  data() {
    return {
      activeTab: 'status',

      // Вкладка Статус
      status: null,
      statusError: '',
      statusLoading: false,
      actionLoading: null,
      actionError: '',
      keepAliveSuccess: false,

      // Вкладка Настройки
      wakeupOptions: [],
      selectedWakeup: null,
      settingsError: '',
      settingsSuccess: '',
      settingsLoading: false,
      saving: false,

      chargingProtection: true,
      chargingProtectionLoading: false,

      capabilities: null,

      // Вкладка Маяк (BLE)
      ble: { supported: null, enabled: false, target: null, present: false },
      bleDevices: [],
      bleScanning: false,
      bleScanned: false,
      bleBusy: false,
      bleError: '',
      bleGraceMinutes: 10,
      bleGraceSaving: false,
    };
  },

  computed: {
    tabs() {
      return [
        { value: 'status',   label: this.$t('power.power.tab_status') },
        { value: 'settings', label: this.$t('power.power.tab_settings') },
        { value: 'beacon',   label: this.$t('power.power.tab_beacon') },
      ];
    },

    uptimeLabel() {
      if (!this.status || this.status.uptime == null) return '—';
      const totalSeconds = Math.floor(this.status.uptime);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      return this.$t('power.power.uptime_format', { h: hours, m: String(minutes).padStart(2, '0') });
    },

    wakeupLabel() {
      if (!this.status || !this.status.wakeup) return this.$t('power.power.wakeup_not_set');
      return this.status.wakeup;
    },

    keepAliveLabel() {
      if (!this.status || this.status.keep_alive_seconds == null) return this.$t('power.power.keep_alive_not_active');
      const s = this.status.keep_alive_seconds;
      const m = Math.floor(s / 60);
      const sec = s % 60;
      if (m > 0) return this.$t('power.power.keep_alive_remaining', { m, s: String(sec).padStart(2, '0') });
      return this.$t('power.power.keep_alive_remaining_sec', { s });
    }
  },

  methods: {
    batteryVariant(value) {
      if (value < 20) return 'critical';
      if (value < 40) return 'warning';
      return 'normal';
    },

    async loadStatus() {
      this.statusError = '';
      this.statusLoading = true;
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000);
        const response = await fetch('/api/power/status', {
          credentials: 'same-origin',
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        const result = await response.json();
        if (!response.ok) {
          this.statusError = result.error || this.$t('power.power.error_load');
          return;
        }
        this.status = result;
      } catch (err) {
        if (err.name === 'AbortError') {
          this.statusError = this.$t('power.power.error_timeout');
        } else {
          this.statusError = this.$t('http.common.error_connection');
        }
      } finally {
        this.statusLoading = false;
      }
    },

    async loadSettings() {
      this.settingsError = '';
      this.settingsLoading = true;
      try {
        const [wakeupRes, protRes] = await Promise.all([
          fetch('/api/power/wakeup', { credentials: 'same-origin' }),
          fetch('/api/power/charging-protection', { credentials: 'same-origin' }),
        ]);
        const wakeupResult = await wakeupRes.json();
        if (!wakeupRes.ok) {
          this.settingsError = wakeupResult.error || this.$t('power.power.error_load_settings');
          return;
        }
        this.wakeupOptions = wakeupResult.options || [];
        this.selectedWakeup = wakeupResult.current || 'disabled';

        const protResult = await protRes.json();
        if (protRes.ok) {
          this.chargingProtection = !!protResult.enabled;
        }
      } catch (err) {
        this.settingsError = this.$t('http.common.error_connection');
      } finally {
        this.settingsLoading = false;
      }
    },

    async onChargingProtectionToggle(value) {
      this.settingsError = '';
      this.settingsSuccess = '';
      this.chargingProtectionLoading = true;
      try {
        const response = await fetch('/api/power/charging-protection', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: value })
        });
        const result = await response.json();
        if (!response.ok) {
          this.settingsError = result.error || this.$t('power.power.error_save');
          this.chargingProtection = !value;
          return;
        }
        this.chargingProtection = !!result.enabled;
        this.settingsSuccess = this.$t('power.power.settings_saved');
      } catch (err) {
        this.settingsError = this.$t('http.common.error_connection');
        this.chargingProtection = !value;
      } finally {
        this.chargingProtectionLoading = false;
      }
    },

    async powerKeepAlive() {
      this.actionError = '';
      this.actionLoading = 'keep_alive';
      try {
        const response = await fetch('/api/power/keep_alive', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ minutes: 5 })
        });
        const result = await response.json();
        if (!response.ok) {
          this.actionError = result.error || this.$t('common.error');
          return;
        }
        this.keepAliveSuccess = true;
        setTimeout(() => { this.keepAliveSuccess = false; }, 2000);
        await this.loadStatus();
      } catch (err) {
        this.actionError = this.$t('http.common.error_connection');
      } finally {
        this.actionLoading = null;
      }
    },

    async powerReboot() {
      if (!confirm(this.$t('power.power.confirm_reboot'))) return;
      this.actionError = '';
      this.actionLoading = 'reboot';
      try {
        const response = await fetch('/api/power/reboot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ reason: 'manual' })
        });
        const result = await response.json();
        if (!response.ok) {
          this.actionError = result.error || this.$t('power.power.error_reboot');
        }
      } catch (err) {
        this.actionError = this.$t('http.common.error_connection');
      } finally {
        this.actionLoading = null;
      }
    },

    async powerShutdown() {
      if (!confirm(this.$t('power.power.confirm_shutdown'))) return;
      this.actionError = '';
      this.actionLoading = 'shutdown';
      try {
        const response = await fetch('/api/power/shutdown', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify('manual')
        });
        const result = await response.json();
        if (!response.ok) {
          this.actionError = result.error || this.$t('power.power.error_shutdown');
        }
      } catch (err) {
        this.actionError = this.$t('http.common.error_connection');
      } finally {
        this.actionLoading = null;
      }
    },

    async loadCapabilities() {
      try {
        const response = await fetch('/api/power/capabilities', { credentials: 'same-origin' });
        const result = await response.json();
        if (response.ok) {
          this.capabilities = result;
        }
      } catch (err) {
        // non-fatal: fall back to null (hide conditional sections)
      }
    },

    async saveWakeup() {
      this.settingsError = '';
      this.settingsSuccess = '';
      this.saving = true;
      try {
        const response = await fetch('/api/power/wakeup', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ value: this.selectedWakeup })
        });
        const result = await response.json();
        if (!response.ok) {
          this.settingsError = result.error || this.$t('power.power.error_save');
          return;
        }
        this.settingsSuccess = this.$t('power.power.settings_saved');
        // Обновить поле wakeup на вкладке Статус
        if (this.status) {
          this.status = { ...this.status, wakeup: this.selectedWakeup === 'disabled' ? null : this.selectedWakeup };
        }
      } catch (err) {
        this.settingsError = this.$t('http.common.error_connection');
      } finally {
        this.saving = false;
      }
    },

    async loadBleConfig() {
      try {
        const response = await fetch('/api/power/ble/config', { credentials: 'same-origin' });
        const result = await response.json();
        if (response.ok) {
          this.ble = {
            supported: !!result.supported,
            enabled: !!result.enabled,
            target: result.target || null,
            present: !!result.present,
          };
          if (result.grace_minutes != null) {
            this.bleGraceMinutes = result.grace_minutes;
          }
        }
      } catch (err) {
        // non-fatal: leave defaults (hide the tab body only on explicit unsupported)
      }
    },

    async saveBleGrace() {
      this.bleError = '';
      const minutes = Math.round(Number(this.bleGraceMinutes));
      if (!Number.isFinite(minutes) || minutes < 1 || minutes > 120) {
        this.bleError = this.$t('power.power.ble_grace_invalid');
        return;
      }
      this.bleGraceSaving = true;
      try {
        const response = await fetch('/api/power/ble/grace', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ minutes })
        });
        const result = await response.json();
        if (!response.ok) {
          this.bleError = result.error || this.$t('power.power.error_save');
          return;
        }
        this.bleGraceMinutes = result.grace_minutes;
      } catch (err) {
        this.bleError = this.$t('http.common.error_connection');
      } finally {
        this.bleGraceSaving = false;
      }
    },

    async onBleToggle(value) {
      this.bleError = '';
      this.bleBusy = true;
      try {
        const response = await fetch('/api/power/ble/enabled', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: value })
        });
        const result = await response.json();
        if (!response.ok) {
          this.bleError = result.error || this.$t('power.power.error_save');
          this.ble.enabled = !value;
          return;
        }
        await this.loadBleConfig();
      } catch (err) {
        this.bleError = this.$t('http.common.error_connection');
        this.ble.enabled = !value;
      } finally {
        this.bleBusy = false;
      }
    },

    async scanBle() {
      this.bleError = '';
      this.bleScanning = true;
      this.bleScanned = false;
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000);
        const response = await fetch('/api/power/ble/scan', {
          credentials: 'same-origin',
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        const result = await response.json();
        if (!response.ok) {
          this.bleError = result.error || this.$t('power.power.ble_error_scan');
          return;
        }
        this.bleDevices = result.devices || [];
        this.bleScanned = true;
      } catch (err) {
        this.bleError = err.name === 'AbortError'
          ? this.$t('power.power.error_timeout')
          : this.$t('http.common.error_connection');
      } finally {
        this.bleScanning = false;
      }
    },

    async selectBeacon(dev) {
      this.bleError = '';
      this.bleBusy = true;
      try {
        const response = await fetch('/api/power/ble/target', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mac: dev.mac, name: dev.name || null })
        });
        const result = await response.json();
        if (!response.ok) {
          this.bleError = result.error || this.$t('power.power.error_save');
          return;
        }
        this.bleDevices = [];
        this.bleScanned = false;
        await this.loadBleConfig();
      } catch (err) {
        this.bleError = this.$t('http.common.error_connection');
      } finally {
        this.bleBusy = false;
      }
    },

    async changeBeacon() {
      this.bleError = '';
      this.bleBusy = true;
      try {
        const response = await fetch('/api/power/ble/clear', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        const result = await response.json();
        if (!response.ok) {
          this.bleError = result.error || this.$t('power.power.error_save');
          return;
        }
        await this.loadBleConfig();
      } catch (err) {
        this.bleError = this.$t('http.common.error_connection');
      } finally {
        this.bleBusy = false;
      }
    }
  },

  async mounted() {
    await Promise.all([this.loadStatus(), this.loadSettings(), this.loadCapabilities(), this.loadBleConfig()]);
  }
};

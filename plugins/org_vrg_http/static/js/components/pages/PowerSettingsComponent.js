// Компонент страницы питания (PiSugar UPS)
const PowerSettingsComponent = {
  components: { TabSwitch, ProgressBar, Icon },
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('http.power.title') }}</h1>
        <div v-if="statusLoading" class="spinner spinner-sm"></div>
        <button v-else class="btn btn-icon" @click="loadStatus" :disabled="statusLoading" :title="$t('http.common.refresh')">↻</button>
      </div>

      <tab-switch
        v-if="status !== null"
        v-model="activeTab"
        :tabs="tabs"
        style="margin-bottom: var(--spacing-lg);"></tab-switch>

      <!-- Вкладка: Статус -->
      <div v-show="activeTab === 'status'">
        <div v-if="statusError" class="alert alert-error">{{ statusError }}</div>
        <div v-if="actionError" class="alert alert-error">{{ actionError }}</div>

        <div v-if="status !== null" class="info-block">
          <div class="section-title">{{ $t('http.power.battery_title') }}</div>

          <div class="info-rows">
            <!-- Заряд батареи -->
            <div class="info-row">
              <span class="info-label">{{ $t('http.power.charge_label') }}</span>
              <progress-bar
                :value="status ? status.battery_percent : 0"
                :variant="batteryVariant(status ? status.battery_percent : 0)"
                :show-label="true"
                style="width: 160px;"
              ></progress-bar>
            </div>

            <!-- Статус зарядки -->
            <div class="info-row">
              <span class="info-label">{{ $t('http.power.power_label') }}</span>
              <span class="status-indicator" style="padding: 3px 8px;">
                <span class="status-dot" :class="{ active: status && status.charging }"></span>
                <span>{{ status ? (status.charging ? $t('http.power.charging') : $t('http.power.on_battery')) : '—' }}</span>
              </span>
            </div>

            <!-- Температура PiSugar -->
            <div class="info-row">
              <span class="info-label">{{ $t('http.power.temp_label') }}</span>
              <strong>{{ status ? status.temp + ' °C' : '—' }}</strong>
            </div>

            <!-- Время работы -->
            <div class="info-row">
              <span class="info-label">{{ $t('http.power.uptime_label') }}</span>
              <strong>{{ uptimeLabel }}</strong>
            </div>

            <!-- Режим пробуждения -->
            <div class="info-row">
              <span class="info-label">{{ $t('http.power.wakeup_label') }}</span>
              <strong>{{ wakeupLabel }}</strong>
            </div>

            <!-- Keep alive -->
            <div class="info-row">
              <span class="info-label">{{ $t('http.power.keep_alive_label') }}</span>
              <strong>{{ keepAliveLabel }}</strong>
            </div>
          </div>
        </div>

        <div style="display: flex; gap: var(--spacing-sm); margin-top: var(--spacing-lg);">
          <button class="btn btn-ghost" @click="powerKeepAlive" :disabled="actionLoading">
            {{ actionLoading === 'keep_alive' ? $t('http.power.keep_alive_wait') : keepAliveSuccess ? $t('common.success') : $t('http.power.keep_alive_btn') }}
          </button>
          <button class="btn btn-ghost" @click="powerReboot" :disabled="actionLoading">
            {{ actionLoading === 'reboot' ? $t('http.power.rebooting') : $t('http.power.reboot_btn') }}
          </button>
          <button class="btn btn-ghost-danger" @click="powerShutdown" :disabled="actionLoading">
            {{ actionLoading === 'shutdown' ? $t('http.power.shutting_down') : $t('http.power.shutdown_btn') }}
          </button>
        </div>

      </div>

      <!-- Вкладка: Настройки -->
      <div v-show="activeTab === 'settings'">
        <div v-if="settingsError" class="alert alert-error">{{ settingsError }}</div>
        <div v-if="settingsSuccess" class="alert alert-success">{{ settingsSuccess }}</div>

        <div v-if="selectedWakeup !== null" class="info-block">
          <div class="section-title">{{ $t('http.power.wakeup_label') }}</div>
          <p style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary);">
            {{ $t('http.power.wakeup_description') }}
          </p>

          <div style="max-width: 400px;">
            <div style="margin-bottom: var(--spacing-md);">
              <label style="display: block; margin-bottom: var(--spacing-sm); color: var(--color-text-secondary); font-size: 0.875rem;">
                {{ $t('http.power.wakeup_mode_label') }}
              </label>
              <select
                v-model="selectedWakeup"
                class="form-input"
                :disabled="saving"
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
              :disabled="saving || settingsLoading"
            >
              {{ saving ? $t('common.saving') : $t('common.save') }}
            </button>
          </div>
        </div>
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
    };
  },

  computed: {
    tabs() {
      return [
        { value: 'status',   label: this.$t('http.power.tab_status') },
        { value: 'settings', label: this.$t('http.power.tab_settings') },
      ];
    },

    uptimeLabel() {
      if (!this.status || this.status.uptime == null) return '—';
      const totalSeconds = Math.floor(this.status.uptime);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      return this.$t('http.power.uptime_format', { h: hours, m: String(minutes).padStart(2, '0') });
    },

    wakeupLabel() {
      if (!this.status || !this.status.wakeup) return this.$t('http.power.wakeup_not_set');
      return this.status.wakeup;
    },

    keepAliveLabel() {
      if (!this.status || this.status.keep_alive_seconds == null) return this.$t('http.power.keep_alive_not_active');
      const s = this.status.keep_alive_seconds;
      const m = Math.floor(s / 60);
      const sec = s % 60;
      if (m > 0) return this.$t('http.power.keep_alive_remaining', { m, s: String(sec).padStart(2, '0') });
      return this.$t('http.power.keep_alive_remaining_sec', { s });
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
          this.statusError = result.error || this.$t('http.power.error_load');
          return;
        }
        this.status = result;
      } catch (err) {
        if (err.name === 'AbortError') {
          this.statusError = this.$t('http.power.error_timeout');
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
        const response = await fetch('/api/power/wakeup', { credentials: 'same-origin' });
        const result = await response.json();
        if (!response.ok) {
          this.settingsError = result.error || this.$t('http.power.error_load_settings');
          return;
        }
        this.wakeupOptions = result.options || [];
        this.selectedWakeup = result.current || 'disabled';
      } catch (err) {
        this.settingsError = this.$t('http.common.error_connection');
      } finally {
        this.settingsLoading = false;
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
      if (!confirm(this.$t('http.power.confirm_reboot'))) return;
      this.actionError = '';
      this.actionLoading = 'reboot';
      try {
        const response = await fetch('/api/power/reboot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({})
        });
        const result = await response.json();
        if (!response.ok) {
          this.actionError = result.error || this.$t('http.power.error_reboot');
        }
      } catch (err) {
        this.actionError = this.$t('http.common.error_connection');
      } finally {
        this.actionLoading = null;
      }
    },

    async powerShutdown() {
      if (!confirm(this.$t('http.power.confirm_shutdown'))) return;
      this.actionError = '';
      this.actionLoading = 'shutdown';
      try {
        const response = await fetch('/api/power/shutdown', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({})
        });
        const result = await response.json();
        if (!response.ok) {
          this.actionError = result.error || this.$t('http.power.error_shutdown');
        }
      } catch (err) {
        this.actionError = this.$t('http.common.error_connection');
      } finally {
        this.actionLoading = null;
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
          this.settingsError = result.error || this.$t('http.power.error_save');
          return;
        }
        this.settingsSuccess = this.$t('http.power.settings_saved');
        // Обновить поле wakeup на вкладке Статус
        if (this.status) {
          this.status = { ...this.status, wakeup: this.selectedWakeup === 'disabled' ? null : this.selectedWakeup };
        }
      } catch (err) {
        this.settingsError = this.$t('http.common.error_connection');
      } finally {
        this.saving = false;
      }
    }
  },

  async mounted() {
    await Promise.all([this.loadStatus(), this.loadSettings()]);
  }
};

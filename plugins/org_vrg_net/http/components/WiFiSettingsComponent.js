// Компонент настройки WiFi сетей (AP и Client)
const WiFiSettingsComponent = {
  components: {
    TabSwitch,
    Icon
  },
  emits: ['navigate'],
  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('net.wifi.title') }}</h1>
        <div v-if="loading" class="spinner spinner-sm"></div>
        <button v-else class="btn btn-icon" @click="loadConfig" :disabled="loading" :title="$t('http.common.refresh')">↻</button>
      </div>

      <div v-if="success" class="alert alert-success">
        {{ success }}
      </div>

      <div v-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <template v-if="!initialLoading">
      <tab-switch v-model="activeTab" :tabs="tabs" style="margin-bottom: var(--spacing-lg);"></tab-switch>

      <!-- Вкладка: Общие -->
      <div v-show="activeTab === 'general'">
        <!-- Режим работы WiFi -->
        <div class="section-title" style="margin-bottom: var(--spacing-md);">{{ $t('net.wifi.mode_title') }}</div>

        <tab-switch
          v-model="mode"
          :tabs="modeTabs"
          :disabled="loading"
          @update:modelValue="onModeChange"
          style="margin-bottom: var(--spacing-md);"
        ></tab-switch>

        <!-- IP выбранного режима -->
        <div v-if="modeIp" class="info-block" style="margin-bottom: var(--spacing-md);">
          {{ $t('net.wifi.ip_label') }} <code style="background: var(--color-bg-tertiary); padding: 2px 6px; border-radius: var(--radius-sm);">{{ modeIp }}</code>
        </div>

        <p style="color: var(--color-text-secondary);">
          {{ $t('net.wifi.mode_description') }}
        </p>
      </div>

      <!-- Вкладка: AP -->
      <div v-show="activeTab === 'ap'">
        <div class="info-block">
          <div class="section-title">{{ $t('net.wifi.ap_settings_title') }}</div>

          <form @submit.prevent="saveApConfig" style="max-width: 600px;">
            <div class="form-group">
              <label class="form-label" for="ap-ssid">{{ $t('net.wifi.ssid_label') }}</label>
              <input
                type="text"
                id="ap-ssid"
                class="form-input"
                v-model="ap.ssid"
                :disabled="loading"
                placeholder="MyAccessPoint"
                required
              />
            </div>

            <div class="form-group">
              <label class="form-label" for="ap-password">{{ $t('net.wifi.password_label') }}</label>
              <input
                type="password"
                id="ap-password"
                class="form-input"
                v-model="ap.password"
                :disabled="loading"
                :placeholder="$t('net.wifi.password_placeholder')"
                minlength="8"
              />
              <span class="form-hint">
                {{ $t('net.wifi.password_hint') }}
              </span>
            </div>

            <div style="display: flex; gap: var(--spacing-md);">
              <button
                type="submit"
                class="btn btn-primary"
                :disabled="loading"
              >
                {{ loading ? $t('common.saving') : $t('common.save') }}
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Вкладка: Client -->
      <div v-show="activeTab === 'client'">
        <div class="info-block">
          <div class="section-title">{{ $t('net.wifi.client_settings_title') }}</div>

          <form @submit.prevent="saveWifiConfig" style="max-width: 600px;">
            <div class="form-group">
              <label class="form-label" for="wifi-ssid">{{ $t('net.wifi.ssid_label') }}</label>
              <input
                type="text"
                id="wifi-ssid"
                class="form-input"
                v-model="wifi.ssid"
                :disabled="loading"
                placeholder="MyHomeWiFi"
                required
              />
            </div>

            <div class="form-group">
              <label class="form-label" for="wifi-password">{{ $t('net.wifi.password_label') }}</label>
              <input
                type="password"
                id="wifi-password"
                class="form-input"
                v-model="wifi.password"
                :disabled="loading"
                :placeholder="$t('net.wifi.password_placeholder')"
              />
            </div>

            <div style="display: flex; gap: var(--spacing-md);">
              <button
                type="submit"
                class="btn btn-primary"
                :disabled="loading"
              >
                {{ loading ? $t('common.saving') : $t('common.save') }}
              </button>
            </div>
          </form>
        </div>
      </div>
      </template>
    </div>
  `,
  data() {
    return {
      activeTab: 'general',
      mode: 'off',
      radioEnabled: false,
      ap: {
        enabled: false,
        ssid: '',
        password: '',
        ip: ''
      },
      wifi: {
        enabled: false,
        ssid: '',
        password: '',
        ip: ''
      },
      error: '',
      success: '',
      loading: false,
      initialLoading: true
    };
  },

  computed: {
    tabs() {
      return [
        { value: 'general', label: this.$t('net.wifi.tab_general') },
        { value: 'ap', label: this.$t('net.wifi.ap_title') },
        { value: 'client', label: this.$t('net.wifi.client_title') }
      ];
    },
    modeTabs() {
      return [
        { value: 'client', label: this.$t('net.wifi.client_title') },
        { value: 'ap', label: this.$t('net.wifi.ap_title') },
        { value: 'off', label: this.$t('net.wifi.mode_off') }
      ];
    },
    modeIp() {
      if (this.mode === 'client') return this.wifi.ip || '';
      if (this.mode === 'ap') return this.ap.ip || '';
      return '';
    }
  },

  methods: {
    async onModeChange(mode) {
      this.error = '';
      this.success = '';
      this.loading = true;

      try {
        const response = await fetch('/api/net/wifi_mode', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'same-origin',
          body: JSON.stringify({ mode })
        });

        if (!response.ok) {
          const data = await response.json();
          this.error = data.error || this.$t('net.wifi.error_mode');
          this.loading = false;
          // Откатываем изменение в UI
          await this.loadConfig();
          return;
        }

        this.success = this.$t('net.wifi.mode_changed');

        // Перезагружаем данные для обновления IP/состояния
        setTimeout(() => {
          this.loadConfig();
        }, 1000);

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('WiFi mode change error:', err);
        this.loading = false;
        await this.loadConfig();
      }
    },

    async loadConfig() {
      this.error = '';
      this.success = '';
      this.loading = true;

      try {
        const response = await fetch('/api/net/connection_config', {
          method: 'GET',
          credentials: 'same-origin'
        });

        if (!response.ok) {
          const data = await response.json();
          this.error = data.error || this.$t('net.wifi.error_load');
          this.loading = false;
          return;
        }

        const data = await response.json();

        // Загружаем состояние WiFi радио
        this.radioEnabled = data.radio_enabled !== undefined ? data.radio_enabled : true;

        // Загружаем данные для AP
        if (data.ap) {
          this.ap.enabled = data.ap.enabled || false;
          this.ap.ssid = data.ap.ssid || '';
          this.ap.password = '';//data.ap.password || '';
          this.ap.ip = data.ap.ip || '';
        }

        // Загружаем данные для WiFi Client
        if (data.wifi) {
          this.wifi.enabled = data.wifi.enabled || false;
          this.wifi.ssid = data.wifi.ssid || '';
          this.wifi.password = '';//data.wifi.password || '';
          this.wifi.ip = data.wifi.ip || '';
        }

        // Определяем текущий режим по активным соединениям
        this.mode = this.deriveMode();

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Load WiFi config error:', err);
      } finally {
        this.loading = false;
        this.initialLoading = false;
      }
    },

    deriveMode() {
      if (!this.radioEnabled) return 'off';
      if (this.ap.enabled) return 'ap';
      if (this.wifi.enabled) return 'client';
      return 'off';
    },

    async saveApConfig() {
      this.error = '';
      this.success = '';
      this.loading = true;

      try {
        const response = await fetch('/api/net/connection_config', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'same-origin',
          body: JSON.stringify({
            type: 'ap',
            ssid: this.ap.ssid,
            ...(this.ap.password ? { password: this.ap.password } : {})
          })
        });

        const data = await response.json();

        if (!response.ok) {
          this.error = data.error || this.$t('net.wifi.error_save_ap');
          this.loading = false;
          return;
        }

        this.success = this.$t('net.wifi.ap_saved');

        // Перезагружаем данные для обновления IP
        setTimeout(() => {
          this.loadConfig();
        }, 1500);

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Save AP config error:', err);
      } finally {
        this.loading = false;
      }
    },

    async saveWifiConfig() {
      this.error = '';
      this.success = '';
      this.loading = true;

      try {
        const response = await fetch('/api/net/connection_config', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'same-origin',
          body: JSON.stringify({
            type: 'wifi',
            ssid: this.wifi.ssid,
            ...(this.wifi.password ? { password: this.wifi.password } : {})
          })
        });

        const data = await response.json();

        if (!response.ok) {
          this.error = data.error || this.$t('net.wifi.error_save_client');
          this.loading = false;
          return;
        }

        this.success = this.$t('net.wifi.client_saved');

        // Перезагружаем данные для обновления IP
        setTimeout(() => {
          this.loadConfig();
        }, 1500);

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Save WiFi config error:', err);
      } finally {
        this.loading = false;
      }
    }
  },
  async mounted() {
    await this.loadConfig();
  }
};

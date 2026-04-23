// Компонент настройки WiFi сетей (AP и Client)
const WiFiSettingsComponent = {
  components: {
    ToggleSwitch,
    TabSwitch,
    Icon
  },
  emits: ['navigate'],
  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('http.wifi.title') }}</h1>
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
        <!-- Включение WiFi модуля -->
        <div class="info-block">
          <div style="display: flex; align-items: center; gap: var(--spacing-md);">
            <div class="section-title" style="margin-bottom: 0;">{{ $t('http.wifi.module_title') }}</div>
            <toggle-switch
              v-model="radioEnabled"
              :disabled="loading"
              @update:modelValue="onWifiBlock"
            ></toggle-switch>
          </div>
          <p style="margin-top: var(--spacing-sm); color: var(--color-text-secondary);">
            {{ $t('http.wifi.module_description') }}
          </p>
        </div>

        <!-- Режим работы WiFi -->
        <div class="section-title" style="margin-bottom: var(--spacing-md);">{{ $t('http.wifi.mode_title') }}</div>

        <div style="display: flex; gap: var(--spacing-md); flex-wrap: wrap; margin-bottom: var(--spacing-md);">
          <!-- Access Point -->
          <div class="info-block" style="flex: 1 1 calc(50% - var(--spacing-md)); min-width: 240px; margin-bottom: 0;">
            <div style="display: flex; align-items: center; gap: var(--spacing-md);">
              <div class="section-title" style="margin-bottom: 0;">{{ $t('http.wifi.ap_title') }}</div>
              <toggle-switch
                v-model="ap.enabled"
                :disabled="loading"
                @update:modelValue="onApToggle"
              ></toggle-switch>
            </div>
            <p style="margin-top: var(--spacing-sm); color: var(--color-text-secondary);">
              {{ $t('http.wifi.ap_description') }}
            </p>
            <div v-if="ap.enabled && ap.ip" style="margin-top: var(--spacing-sm);">
              {{ $t('http.wifi.ip_label') }} <code style="background: var(--color-bg-tertiary); padding: 2px 6px; border-radius: var(--radius-sm);">{{ ap.ip }}</code>
            </div>
          </div>

          <!-- Client -->
          <div class="info-block" style="flex: 1 1 calc(50% - var(--spacing-md)); min-width: 240px; margin-bottom: 0;">
            <div style="display: flex; align-items: center; gap: var(--spacing-md);">
              <div class="section-title" style="margin-bottom: 0;">{{ $t('http.wifi.client_title') }}</div>
              <toggle-switch
                v-model="wifi.enabled"
                :disabled="loading"
                @update:modelValue="onWifiToggle"
              ></toggle-switch>
            </div>
            <p style="margin-top: var(--spacing-sm); color: var(--color-text-secondary);">
              {{ $t('http.wifi.client_description') }}
            </p>
            <div v-if="wifi.enabled && wifi.ip" style="margin-top: var(--spacing-sm);">
              {{ $t('http.wifi.ip_label') }} <code style="background: var(--color-bg-tertiary); padding: 2px 6px; border-radius: var(--radius-sm);">{{ wifi.ip }}</code>
            </div>
          </div>
        </div>

        <p style="color: var(--color-text-secondary); margin-bottom: var(--spacing-xs);">
          {{ $t('http.wifi.mode_note1') }}
        </p>
        <p style="color: var(--color-text-secondary);">
          {{ $t('http.wifi.mode_note2') }}
        </p>
      </div>

      <!-- Вкладка: AP -->
      <div v-show="activeTab === 'ap'">
        <div v-if="ap.ip" class="info-block" style="margin-bottom: var(--spacing-md);">
          <strong>{{ $t('http.wifi.ip_router') }}</strong>
          <code style="background: var(--color-bg-tertiary); padding: 2px 6px; border-radius: var(--radius-sm);">{{ ap.ip }}</code>
        </div>

        <div class="info-block">
          <div class="section-title">{{ $t('http.wifi.ap_settings_title') }}</div>

          <form @submit.prevent="saveApConfig" style="max-width: 600px;">
            <div class="form-group">
              <toggle-switch
                v-model="ap.autoconnect"
                :disabled="loading"
                :label="$t('http.common.autoconnect')"
              ></toggle-switch>
            </div>

            <div class="form-group">
              <label class="form-label" for="ap-ssid">{{ $t('http.wifi.ssid_label') }}</label>
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
              <label class="form-label" for="ap-password">{{ $t('http.wifi.password_label') }}</label>
              <input
                type="password"
                id="ap-password"
                class="form-input"
                v-model="ap.password"
                :disabled="loading"
                :placeholder="$t('http.wifi.password_placeholder')"
                minlength="8"
              />
              <span class="form-hint">
                {{ $t('http.wifi.password_hint') }}
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
        <div v-if="wifi.ip" class="info-block" style="margin-bottom: var(--spacing-md);">
          <strong>{{ $t('http.wifi.ip_client') }}</strong>
          <code style="background: var(--color-bg-tertiary); padding: 2px 6px; border-radius: var(--radius-sm);">{{ wifi.ip }}</code>
        </div>

        <div class="info-block">
          <div class="section-title">{{ $t('http.wifi.client_settings_title') }}</div>

          <form @submit.prevent="saveWifiConfig" style="max-width: 600px;">
            <div class="form-group">
              <toggle-switch
                v-model="wifi.autoconnect"
                :disabled="loading"
                :label="$t('http.common.autoconnect')"
              ></toggle-switch>
            </div>

            <div class="form-group">
              <label class="form-label" for="wifi-ssid">{{ $t('http.wifi.ssid_label') }}</label>
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
              <label class="form-label" for="wifi-password">{{ $t('http.wifi.password_label') }}</label>
              <input
                type="password"
                id="wifi-password"
                class="form-input"
                v-model="wifi.password"
                :disabled="loading"
                :placeholder="$t('http.wifi.password_placeholder')"
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
      radioEnabled: false,
      ap: {
        enabled: false,
        autoconnect: false,
        ssid: '',
        password: '',
        ip: ''
      },
      wifi: {
        enabled: false,
        autoconnect: false,
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
        { value: 'general', label: this.$t('http.wifi.tab_general') },
        { value: 'ap', label: this.$t('http.wifi.ap_title') },
        { value: 'client', label: this.$t('http.wifi.client_title') }
      ];
    }
  },

  methods: {
    async onWifiBlock(enabled) {
      this.error = '';
      this.success = '';
      this.loading = true;

      try {
        const response = await fetch('/api/net/wifi_block', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'same-origin',
          body: JSON.stringify({
            blocked: !enabled
          })
        });

        if (!response.ok) {
          const data = await response.json();
          this.error = data.error || this.$t('http.wifi.error_module');
          this.loading = false;
          // Откатываем изменение в UI
          await this.loadConfig();
          return;
        }

        this.success = enabled ? this.$t('http.wifi.module_enabled') : this.$t('http.wifi.module_disabled');

        // Перезагружаем данные
        setTimeout(() => {
          this.loadConfig();
        }, 1000);

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Radio toggle error:', err);
        this.loading = false;
        await this.loadConfig();
      }
    },

    async onApToggle(value) {
      // Если включаем AP, выключаем WiFi
      if (value && this.wifi.enabled) {
        this.error = '';
        this.success = '';
        await this.switchConnection('wifi', false);
      }

      // Применяем изменение для AP
      await this.switchConnection('ap', value);
    },

    async onWifiToggle(value) {
      // Если включаем WiFi, выключаем AP
      if (value && this.ap.enabled) {
        this.error = '';
        this.success = '';
        await this.switchConnection('ap', false);
      }

      // Применяем изменение для WiFi
      await this.switchConnection('wifi', value);
    },

    async switchConnection(type, enabled) {
      this.loading = true;

      try {
        const response = await fetch('/api/net/connection_enable', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'same-origin',
          body: JSON.stringify({
            type: type,
            enabled: enabled
          })
        });

        if (!response.ok) {
          const data = await response.json();
          this.error = data.error || this.$t('http.wifi.error_module');
          this.loading = false;
          // Откатываем изменение в UI
          await this.loadConfig();
          return;
        }

        this.success = enabled ? this.$t('http.wifi.mode_enabled') : this.$t('http.wifi.mode_disabled');

        // Перезагружаем данные
        setTimeout(() => {
          this.loadConfig();
        }, 1000);

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Switch mode error:', err);
        this.loading = false;
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
          this.error = data.error || this.$t('http.wifi.error_load');
          this.loading = false;
          return;
        }

        const data = await response.json();

        // Загружаем состояние WiFi радио
        this.radioEnabled = data.radio_enabled !== undefined ? data.radio_enabled : true;

        // Загружаем данные для AP
        if (data.ap) {
          this.ap.enabled = data.ap.enabled || false;
          this.ap.autoconnect = data.ap.autoconnect || false;
          this.ap.ssid = data.ap.ssid || '';
          this.ap.password = '';//data.ap.password || '';
          this.ap.ip = data.ap.ip || '';
        }

        // Загружаем данные для WiFi Client
        if (data.wifi) {
          this.wifi.enabled = data.wifi.enabled || false;
          this.wifi.autoconnect = data.wifi.autoconnect || false;
          this.wifi.ssid = data.wifi.ssid || '';
          this.wifi.password = '';//data.wifi.password || '';
          this.wifi.ip = data.wifi.ip || '';
        }

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Load WiFi config error:', err);
      } finally {
        this.loading = false;
        this.initialLoading = false;
      }
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
            autoconnect: this.ap.autoconnect,
            ssid: this.ap.ssid,
            ...(this.ap.password ? { password: this.ap.password } : {})
          })
        });

        const data = await response.json();

        if (!response.ok) {
          this.error = data.error || this.$t('http.wifi.error_save_ap');
          this.loading = false;
          return;
        }

        this.success = this.$t('http.wifi.ap_saved');

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
            autoconnect: this.wifi.autoconnect,
            ssid: this.wifi.ssid,
            ...(this.wifi.password ? { password: this.wifi.password } : {})
          })
        });

        const data = await response.json();

        if (!response.ok) {
          this.error = data.error || this.$t('http.wifi.error_save_client');
          this.loading = false;
          return;
        }

        this.success = this.$t('http.wifi.client_saved');

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

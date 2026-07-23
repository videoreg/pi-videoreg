// Компонент настройки модема
const ModemSettingsComponent = {
  components: {
    ToggleSwitch,
    TabSwitch,
    ProgressBar,
    Icon
  },
  emits: ['navigate'],
  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('net.modem.title') }}</h1>
        <div v-if="modemInfoLoading" class="spinner spinner-sm"></div>
        <button v-else class="btn btn-icon" @click="refreshAll" :disabled="modemInfoLoading" :title="$t('http.common.refresh')">↻</button>
      </div>

      <div class="content-section">
        <template v-if="!modemInfoLoading">
        <!-- Переключатель вкладок -->
        <tab-switch
          v-model="activeTab"
          :tabs="tabs"
          style="margin-bottom: var(--spacing-lg);"
        ></tab-switch>

        <div v-if="success" class="alert alert-success">
          {{ success }}
        </div>

        <div v-if="error" class="alert alert-error">
          {{ error }}
        </div>

        <!-- Вкладка "Статус" -->
        <div v-if="activeTab === 'status'">
            <div class="info-block">
            <div class="section-title">{{ $t('net.modem.info_title') }}</div>

            <!-- Модем не подключен -->
            <div v-if="!modemInfo || !modemInfo.connected" style="text-align: center; padding: var(--spacing-xl) 0;">
              <div style="font-size: 48px; margin-bottom: var(--spacing-md);">📵</div>
              <p style="color: var(--color-text-secondary); font-size: 16px;">
                {{ $t('net.modem.not_connected') }}
              </p>
              <p style="color: var(--color-text-tertiary); font-size: 14px; margin-top: var(--spacing-sm);">
                {{ $t('net.modem.not_connected_hint') }}
              </p>
            </div>

            <!-- Информация о модеме -->
            <div v-else class="info-rows">
              <div v-if="modemInfo.model" class="info-row">
                <span class="info-label">{{ $t('net.modem.model_label') }}</span>
                <strong>{{ modemInfo.manufacturer ? modemInfo.manufacturer + ' ' : '' }}{{ modemInfo.model }}</strong>
              </div>

              <div v-if="modemInfo.device" class="info-row">
                <span class="info-label">{{ $t('net.modem.device_label') }}</span>
                <code class="code-inline">{{ modemInfo.device }}</code>
              </div>

              <div v-if="modemInfo.operator" class="info-row">
                <span class="info-label">{{ $t('net.modem.operator_label') }}</span>
                <strong>{{ modemInfo.operator }}</strong>
              </div>

              <div v-if="modemInfo.access_tech" class="info-row">
                <span class="info-label">{{ $t('net.modem.access_tech_label') }}</span>
                <strong>{{ modemInfo.access_tech }}</strong>
              </div>

              <div v-if="modemInfo.signal_quality !== null && modemInfo.signal_quality !== undefined" class="info-row">
                <span class="info-label">{{ $t('net.modem.signal_label') }}</span>
                <progress-bar :value="modemInfo.signal_quality" :variant="signalVariant(modemInfo.signal_quality)" :show-label="true" style="width: 160px;"></progress-bar>
              </div>

              <div v-if="ip" class="info-row">
                <span class="info-label">{{ $t('net.modem.ip_label') }}</span>
                <code class="code-inline">{{ ip }}</code>
              </div>
            </div>
          </div>
        </div>

        <!-- Вкладка "Настройка" -->
        <div v-if="activeTab === 'settings'">
          <div class="info-block">
            <form @submit.prevent="saveApn" style="max-width: 600px;">
              <div class="section-title">{{ $t('net.modem.settings_title') }}</div>

              <div class="form-group">
                <label class="form-label" for="apn">{{ $t('net.modem.apn_label') }}</label>
                <input
                  type="text"
                  id="apn"
                  class="form-input"
                  v-model="apn"
                  :disabled="loading"
                  placeholder="internet"
                />
                <span class="form-hint">
                  {{ $t('net.modem.apn_hint') }}
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

          <div class="info-block" style="margin-top: var(--spacing-xl);">
            <div class="section-title">{{ $t('net.modem.info_block_title') }}</div>
            <p style="margin-bottom: var(--spacing-sm); color: var(--color-text-secondary);">
              {{ $t('net.modem.apn_description') }}
            </p>
            <p style="margin-bottom: var(--spacing-sm); color: var(--color-text-secondary);">
              {{ $t('net.modem.apn_examples') }}
            </p>
            <ul style="margin-left: var(--spacing-lg); color: var(--color-text-secondary);">
              <li>МТС: <code class="code-inline">internet.mts.ru</code></li>
              <li>Билайн: <code class="code-inline">internet.beeline.ru</code></li>
              <li>МегаФон: <code class="code-inline">internet</code></li>
              <li>Tele2: <code class="code-inline">internet.tele2.ru</code></li>
              <li>Yota: <code class="code-inline">internet.yota</code></li>
            </ul>
          </div>
        </div>
        </template>
      </div>
    </div>
  `,
  data() {
    return {
      activeTab: 'status',
      apn: '',
      ip: '',
      modemInfo: null,
      modemInfoLoading: true,
      error: '',
      success: '',
      loading: false
    };
  },

  computed: {
    tabs() {
      return [
        { value: 'status', label: this.$t('net.modem.tab_status') },
        { value: 'settings', label: this.$t('net.modem.tab_settings') }
      ];
    }
  },

  methods: {
    signalVariant(quality) {
      if (quality < 40) return 'critical';
      if (quality < 70) return 'warning';
      return 'normal';
    },

    async refreshAll() {
      await Promise.all([this.loadApn(), this.loadModemInfo(), this.loadConnection()]);
    },

    async loadModemInfo() {
      this.modemInfoLoading = true;

      try {
        const response = await fetch('/api/net/modem_info', {
          method: 'GET',
          credentials: 'same-origin'
        });

        if (response.ok) {
          const data = await response.json();
          this.modemInfo = data;
          console.log('Modem info loaded:', data);
        } else {
          // Если ошибка, устанавливаем что модем не подключен
          this.modemInfo = { connected: false };
        }
      } catch (err) {
        console.error('Load modem info error:', err);
        // Не показываем ошибку пользователю, т.к. это некритичная информация
        this.modemInfo = { connected: false };
      } finally {
        this.modemInfoLoading = false;
      }
    },

    async loadApn() {
      this.error = '';
      this.success = '';
      this.loading = true;

      try {
        const response = await fetch('/api/modem/apn', {
          method: 'GET',
          credentials: 'same-origin'
        });

        if (!response.ok) {
          const data = await response.json();
          this.error = data.error || this.$t('net.modem.error_load');
          this.loading = false;
          return;
        }

        const data = await response.json();
        this.apn = data.apn || '';

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Load APN error:', err);
      } finally {
        this.loading = false;
      }
    },

    async loadConnection() {
      // Modem IP comes from the NetworkManager connection; APN is configured
      // separately over AT (see loadApn / saveApn).
      try {
        const response = await fetch('/api/net/connection_config', {
          method: 'GET',
          credentials: 'same-origin'
        });

        if (response.ok) {
          const data = await response.json();
          this.ip = (data.modem && data.modem.ip) || '';
        }
      } catch (err) {
        console.error('Load connection error:', err);
      }
    },

    async saveApn() {
      this.error = '';
      this.success = '';
      this.loading = true;

      try {
        const response = await fetch('/api/modem/apn', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'same-origin',
          body: JSON.stringify({
            apn: this.apn
          })
        });

        const data = await response.json();

        if (!response.ok) {
          this.error = data.error || this.$t('net.modem.error_save');
          this.loading = false;
          return;
        }

        this.success = this.$t('net.modem.saved');

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Save APN error:', err);
      } finally {
        this.loading = false;
      }
    }
  },
  async mounted() {
    await this.loadApn();
    await this.loadModemInfo();
    await this.loadConnection();
  }
};

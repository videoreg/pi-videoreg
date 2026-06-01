// Компонент настройки WireGuard
const WireguardSettingsComponent = {
  components: { TabSwitch, Icon },
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('net.wireguard.title') }}</h1>
        <div v-if="statusLoading" class="spinner spinner-sm"></div>
        <button v-else class="btn btn-icon" @click="loadStatus" :disabled="statusLoading" :title="$t('http.common.refresh')">↻</button>
      </div>

      <div class="content-section">
        <tab-switch
          v-if="!statusLoading"
          v-model="activeTab"
          :tabs="tabs"
          style="margin-bottom: var(--spacing-lg);"
        ></tab-switch>

        <div v-if="success" class="alert alert-success">{{ success }}</div>
        <div v-if="error" class="alert alert-error">{{ error }}</div>

        <!-- Вкладка "Статус" -->
        <div v-if="activeTab === 'status' && !statusLoading">
          <div class="info-block">
            <div class="section-title">{{ $t('net.wireguard.interface_title') }}</div>

            <div v-if="!wgStatus" style="text-align: center; padding: var(--spacing-xl) 0;">
              <p style="color: var(--color-text-secondary);">{{ $t('net.wireguard.no_data') }}</p>
            </div>

            <div v-else-if="wgStatus" class="info-rows">

              <!-- Статус -->
              <div class="info-row">
                <span class="info-label">{{ $t('net.wireguard.status_label') }}</span>
                <span class="status-indicator">
                  <span class="status-dot" :class="{ active: wgStatus.active }"></span>
                  <span>{{ wgStatus.active ? $t('net.wireguard.active') : $t('net.wireguard.inactive') }}</span>
                </span>
              </div>

              <!-- IP -->
              <div v-if="wgStatus.ip_address" class="info-row">
                <span class="info-label">{{ $t('net.wireguard.ip_label') }}</span>
                <code class="code-inline">{{ wgStatus.ip_address }}</code>
              </div>

              <!-- Сервер (endpoint первого пира) -->
              <div v-if="firstPeer && firstPeer.endpoint" class="info-row">
                <span class="info-label">{{ $t('net.wireguard.server_label') }}</span>
                <code class="code-inline">{{ firstPeer.endpoint }}</code>
              </div>

              <!-- Последний handshake -->
              <div v-if="firstPeer && firstPeer.latest_handshake" class="info-row">
                <span class="info-label">{{ $t('net.wireguard.handshake_label') }}</span>
                <span>{{ firstPeer.latest_handshake }}</span>
              </div>

              <!-- Трафик -->
              <div v-if="firstPeer && firstPeer.transfer_received" class="info-row">
                <span class="info-label">{{ $t('net.wireguard.traffic_in') }}</span>
                <span>{{ firstPeer.transfer_received }}</span>
              </div>

              <div v-if="firstPeer && firstPeer.transfer_sent" class="info-row">
                <span class="info-label">{{ $t('net.wireguard.traffic_out') }}</span>
                <span>{{ firstPeer.transfer_sent }}</span>
              </div>

            </div>
          </div>

        </div>

        <!-- Вкладка "Настройка" -->
        <div v-if="activeTab === 'settings'">
          <!-- Генерация ключей -->
          <div style="margin-bottom: var(--spacing-lg);">
            <button
              @click="generateKeys"
              class="btn btn-primary"
              :disabled="loadingKeys"
              style="margin-right: var(--spacing-md);"
            >
              {{ loadingKeys ? $t('net.wireguard.generating') : $t('net.wireguard.generate_keys') }}
            </button>

            <div v-if="generatedKeys" class="info-block" style="margin-top: var(--spacing-md);">
              <div class="section-title">{{ $t('net.wireguard.generated_keys_title') }}</div>

              <div class="form-group">
                <label class="form-label">{{ $t('net.wireguard.private_key') }}</label>
                <div style="display: flex; gap: var(--spacing-sm);">
                  <input
                    type="text"
                    class="form-input"
                    :value="generatedKeys.private_key"
                    readonly
                    style="flex: 1; font-family: monospace; font-size: 0.875rem;"
                  />
                  <button
                    @click="copyToClipboard(generatedKeys.private_key, 'private')"
                    class="btn btn-primary"
                    style="white-space: nowrap;"
                  >
                    {{ copiedPrivate ? $t('net.wireguard.copied') : $t('net.wireguard.copy') }}
                  </button>
                </div>
              </div>

              <div class="form-group" style="margin-bottom: 0;">
                <label class="form-label">{{ $t('net.wireguard.public_key') }}</label>
                <div style="display: flex; gap: var(--spacing-sm);">
                  <input
                    type="text"
                    class="form-input"
                    :value="generatedKeys.public_key"
                    readonly
                    style="flex: 1; font-family: monospace; font-size: 0.875rem;"
                  />
                  <button
                    @click="copyToClipboard(generatedKeys.public_key, 'public')"
                    class="btn btn-primary"
                    style="white-space: nowrap;"
                  >
                    {{ copiedPublic ? $t('net.wireguard.copied') : $t('net.wireguard.copy') }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Редактор конфигурации -->
          <div class="info-block">
            <div class="form-group">
              <label class="form-label">{{ $t('net.wireguard.config_label') }}</label>
              <textarea
                class="form-input"
                v-model="config"
                :disabled="loading"
                rows="20"
                style="font-family: monospace; font-size: 0.875rem; resize: vertical;"
                :placeholder="$t('net.wireguard.config_placeholder')"
              ></textarea>
              <span class="form-hint">{{ $t('net.wireguard.config_hint') }}</span>
            </div>

            <div style="display: flex; gap: var(--spacing-md);">
              <button @click="saveConfig" class="btn btn-primary" :disabled="loading || !config">
                {{ loading ? $t('common.saving') : $t('common.save') }}
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  `,

  data() {
    return {
      activeTab: 'status',
      wgStatus: null,
      statusLoading: true,
      config: '',
      generatedKeys: null,
      error: '',
      success: '',
      loading: false,
      loadingKeys: false,
      copiedPrivate: false,
      copiedPublic: false
    };
  },

  computed: {
    tabs() {
      return [
        { value: 'status', label: this.$t('net.wireguard.tab_status') },
        { value: 'settings', label: this.$t('net.wireguard.tab_settings') }
      ];
    },

    firstPeer() {
      return this.wgStatus && this.wgStatus.peers && this.wgStatus.peers.length > 0
        ? this.wgStatus.peers[0]
        : null;
    }
  },

  methods: {
    async loadStatus() {
      this.statusLoading = true;
      try {
        const response = await fetch('/api/net/wireguard_status', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_load_status');
          return;
        }
        this.wgStatus = data;
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.statusLoading = false;
      }
    },

    async loadConfig() {
      this.error = '';
      this.success = '';
      this.loading = true;
      try {
        const response = await fetch('/api/net/wireguard_config', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_load_config');
          return;
        }
        if (data.exists === false) {
          this.config = '';
          this.success = this.$t('net.wireguard.config_not_found');
          return;
        }
        this.config = data.content || '';
      } catch (err) {
        this.error = this.$t('http.common.error_server');
      } finally {
        this.loading = false;
      }
    },

    async saveConfig() {
      this.error = '';
      this.success = '';
      this.loading = true;
      try {
        const response = await fetch('/api/net/wireguard_config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ content: this.config })
        });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_save_config');
          return;
        }
        this.success = this.$t('net.wireguard.config_saved');
      } catch (err) {
        this.error = this.$t('http.common.error_server');
      } finally {
        this.loading = false;
      }
    },

    async generateKeys() {
      this.error = '';
      this.success = '';
      this.loadingKeys = true;
      this.generatedKeys = null;
      this.copiedPrivate = false;
      this.copiedPublic = false;
      try {
        const response = await fetch('/api/net/generate_wireguard_key', {
          method: 'POST',
          credentials: 'same-origin'
        });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_generate_keys');
          return;
        }
        this.generatedKeys = data;
        this.success = this.$t('net.wireguard.keys_generated');
      } catch (err) {
        this.error = this.$t('http.common.error_server');
      } finally {
        this.loadingKeys = false;
      }
    },

    async copyToClipboard(text, type) {
      try {
        await navigator.clipboard.writeText(text);
        if (type === 'private') {
          this.copiedPrivate = true;
          setTimeout(() => { this.copiedPrivate = false; }, 2000);
        } else {
          this.copiedPublic = true;
          setTimeout(() => { this.copiedPublic = false; }, 2000);
        }
      } catch (err) {
        this.error = this.$t('net.wireguard.error_copy');
      }
    }
  },

  async mounted() {
    await Promise.all([this.loadStatus(), this.loadConfig()]);
  }
};

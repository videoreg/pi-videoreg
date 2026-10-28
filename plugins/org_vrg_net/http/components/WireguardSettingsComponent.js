// Компонент настройки WireGuard
const WireguardSettingsComponent = {
  components: { TabSwitch, Icon, ToggleSwitch },
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
          <!-- Переключатели управления -->
          <div class="info-block">
            <div class="section-title">{{ $t('net.wireguard.control_title') }}</div>

            <!-- Состояние -->
            <div class="form-group" style="display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md);">
              <div>
                <div class="form-label" style="margin-bottom: 2px;">{{ $t('net.wireguard.state_title') }}</div>
                <span class="form-hint">{{ $t('net.wireguard.state_hint') }}</span>
              </div>
              <toggle-switch
                v-model="settings.active"
                :disabled="settingsLoading || togglingState"
                @update:modelValue="onToggleState"
              ></toggle-switch>
            </div>

            <!-- Автоподключение -->
            <div class="form-group" style="display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md);">
              <div>
                <div class="form-label" style="margin-bottom: 2px;">{{ $t('net.wireguard.auto_title') }}</div>
                <span class="form-hint">{{ $t('net.wireguard.auto_hint') }}</span>
              </div>
              <toggle-switch
                v-model="settings.auto"
                :disabled="settingsLoading"
                @update:modelValue="onToggleAuto"
              ></toggle-switch>
            </div>

            <!-- Не подключать для WiFi Client -->
            <div class="form-group" style="display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md); margin-bottom: 0;">
              <div>
                <div class="form-label" style="margin-bottom: 2px;">{{ $t('net.wireguard.skip_on_wifi_title') }}</div>
                <span class="form-hint">{{ $t('net.wireguard.skip_on_wifi_hint') }}</span>
              </div>
              <toggle-switch
                v-model="settings.skip_on_wifi"
                :disabled="settingsLoading"
                @update:modelValue="onToggleSkipOnWifi"
              ></toggle-switch>
            </div>
          </div>

          <!-- Connection: /etc/wireguard/wg0.conf is generated from these fields -->
          <div class="info-block">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md); margin-bottom: var(--spacing-md);">
              <div class="section-title" style="margin-bottom: 0;">{{ $t('net.wireguard.connection_title') }}</div>
              <button class="btn btn-outline btn-sm" @click="showImport = !showImport" :disabled="loading">
                {{ $t('net.wireguard.import') }}
              </button>
            </div>

            <!-- Import: parses a pasted .conf into the fields, saves nothing -->
            <div v-if="showImport" class="form-group">
              <textarea
                class="form-input"
                v-model="importText"
                rows="10"
                style="font-family: monospace; font-size: 0.875rem; resize: vertical;"
              ></textarea>
              <span class="form-hint">{{ $t('net.wireguard.import_hint') }}</span>
              <div style="margin-top: var(--spacing-sm);">
                <button class="btn btn-primary btn-sm" @click="importConfig" :disabled="importing || !importText.trim()">
                  {{ $t('net.wireguard.import_apply') }}
                </button>
              </div>
            </div>

            <div v-if="importIgnored.length" class="alert alert-warning">
              <div>{{ $t('net.wireguard.import_ignored') }}</div>
              <code v-for="line in importIgnored" :key="line" class="code-inline" style="display: block; margin-top: 2px;">{{ line }}</code>
            </div>

            <!-- Device -->
            <div class="section-title">{{ $t('net.wireguard.section_interface') }}</div>

            <div class="form-group">
              <label class="form-label">{{ $t('net.wireguard.field_private_key') }}</label>
              <div style="display: flex; gap: var(--spacing-sm);">
                <input
                  type="password"
                  class="form-input"
                  v-model="form.private_key"
                  :placeholder="hasPrivateKey ? $t('net.wireguard.field_private_key_keep') : ''"
                  :disabled="loading"
                  autocomplete="off"
                  style="flex: 1; font-family: monospace; font-size: 0.875rem;"
                />
                <button class="btn btn-outline" @click="generateKeys" :disabled="loading || loadingKeys" style="white-space: nowrap;">
                  {{ loadingKeys ? $t('net.wireguard.generating') : $t('net.wireguard.generate_keys') }}
                </button>
              </div>
            </div>

            <div v-if="publicKey" class="form-group">
              <label class="form-label">{{ $t('net.wireguard.device_public_key') }}</label>
              <div style="display: flex; gap: var(--spacing-sm);">
                <input
                  type="text"
                  class="form-input"
                  :value="publicKey"
                  readonly
                  style="flex: 1; font-family: monospace; font-size: 0.875rem;"
                />
                <button class="btn btn-outline" @click="copyPublicKey" style="white-space: nowrap;">
                  {{ copiedPublic ? $t('net.wireguard.copied') : $t('net.wireguard.copy') }}
                </button>
              </div>
              <span class="form-hint">{{ $t('net.wireguard.device_public_key_hint') }}</span>
            </div>

            <div class="form-group">
              <label class="form-label">{{ $t('net.wireguard.field_address') }}</label>
              <input type="text" class="form-input" v-model="form.address" :disabled="loading" placeholder="192.168.87.9/24" />
              <span class="form-hint">{{ $t('net.wireguard.field_address_hint') }}</span>
            </div>

            <!-- VPN server -->
            <div class="section-title">{{ $t('net.wireguard.section_peer') }}</div>

            <div class="form-group">
              <label class="form-label">{{ $t('net.wireguard.field_peer_endpoint') }}</label>
              <input type="text" class="form-input" v-model="form.peer_endpoint" :disabled="loading" placeholder="vpn.example.com:51820" />
              <span class="form-hint">{{ $t('net.wireguard.field_peer_endpoint_hint') }}</span>
            </div>

            <div class="form-group">
              <label class="form-label">{{ $t('net.wireguard.field_peer_public_key') }}</label>
              <input
                type="text"
                class="form-input"
                v-model="form.peer_public_key"
                :disabled="loading"
                style="font-family: monospace; font-size: 0.875rem;"
              />
            </div>

            <div class="form-group">
              <label class="form-label">{{ $t('net.wireguard.field_peer_allowed_ips') }}</label>
              <input type="text" class="form-input" v-model="form.peer_allowed_ips" :disabled="loading" placeholder="192.168.87.0/24, 0.0.0.0/0" />
              <span class="form-hint">{{ $t('net.wireguard.field_peer_allowed_ips_hint') }}</span>
            </div>

            <div v-if="form.peer_allowed_ips.trim() && !routesInternet" class="alert alert-warning">
              {{ $t('net.wireguard.no_internet_warning') }}
            </div>

            <div class="form-group">
              <label class="form-label">{{ $t('net.wireguard.field_peer_persistent_keepalive') }}</label>
              <input type="number" class="form-input" v-model="form.peer_persistent_keepalive" :disabled="loading" min="0" max="65535" />
              <span class="form-hint">{{ $t('net.wireguard.field_peer_persistent_keepalive_hint') }}</span>
            </div>

            <!-- Advanced -->
            <div class="section-title">{{ $t('net.wireguard.section_advanced') }}</div>

            <div class="form-group">
              <label class="form-label">{{ $t('net.wireguard.field_mtu') }}</label>
              <input type="number" class="form-input" v-model="form.mtu" :disabled="loading" min="576" max="9000" />
              <span class="form-hint">{{ $t('net.wireguard.field_mtu_hint') }}</span>
            </div>

            <div class="form-group">
              <label class="form-label">{{ $t('net.wireguard.field_peer_preshared_key') }}</label>
              <input
                type="password"
                class="form-input"
                v-model="form.peer_preshared_key"
                :disabled="loading"
                autocomplete="off"
                style="font-family: monospace; font-size: 0.875rem;"
              />
              <span class="form-hint">{{ $t('net.wireguard.field_peer_preshared_key_hint') }}</span>
            </div>

            <p class="form-hint" style="display: block; margin-bottom: var(--spacing-md);">{{ $t('net.wireguard.save_restart_hint') }}</p>

            <button @click="saveConfig" class="btn btn-primary" :disabled="loading">
              {{ loading ? $t('common.saving') : $t('common.save') }}
            </button>
          </div>
        </div>

        <!-- "Routing" tab: which plugins send their outbound traffic through the tunnel -->
        <div v-if="activeTab === 'routing'">
          <div v-if="routingLoading" style="text-align: center; padding: var(--spacing-xl) 0;">
            <div class="spinner spinner-sm" style="display: inline-block;"></div>
          </div>

          <div v-else class="info-block">
            <div class="section-title">{{ $t('net.wireguard.routing_title') }}</div>
            <p class="form-hint" style="display: block; margin-bottom: var(--spacing-md);">{{ $t('net.wireguard.routing_hint') }}</p>

            <div v-if="routingWarning" class="alert alert-warning">{{ routingWarning }}</div>

            <p v-if="routing.plugins.length === 0" style="color: var(--color-text-secondary);">
              {{ $t('net.wireguard.routing_no_plugins') }}
            </p>

            <div
              v-for="(plugin, index) in routing.plugins"
              :key="plugin.id"
              class="form-group"
              :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--spacing-md)', marginBottom: index === routing.plugins.length - 1 ? 0 : null }"
            >
              <div>
                <div class="form-label" style="margin-bottom: 2px;">{{ pluginTitle(plugin) }}</div>
                <span class="form-hint">{{ pluginRouteHint(plugin) }}</span>
              </div>
              <toggle-switch
                v-model="plugin.via_wg"
                :disabled="togglingPlugin === plugin.id"
                @update:modelValue="onTogglePluginRouting(plugin, $event)"
              ></toggle-switch>
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
      settings: {
        active: false,
        auto: true,
        skip_on_wifi: true
      },
      settingsLoading: true,
      togglingState: false,
      routing: {
        plugins: [],
        active: false,
        routing: false,
        default_route: false
      },
      routingLoading: true,
      togglingPlugin: null,
      form: {
        private_key: '',
        address: '',
        mtu: '',
        peer_public_key: '',
        peer_preshared_key: '',
        peer_endpoint: '',
        peer_allowed_ips: '',
        peer_persistent_keepalive: '25'
      },
      hasPrivateKey: false,
      publicKey: '',
      showImport: false,
      importText: '',
      importing: false,
      importIgnored: [],
      error: '',
      success: '',
      loading: false,
      loadingKeys: false,
      copiedPublic: false
    };
  },

  computed: {
    tabs() {
      return [
        { value: 'status', label: this.$t('net.wireguard.tab_status') },
        { value: 'settings', label: this.$t('net.wireguard.tab_settings') },
        { value: 'routing', label: this.$t('net.wireguard.tab_routing') }
      ];
    },

    // Why plugins selected for WireGuard still use the main connection, if they do
    routingWarning() {
      if (!this.routing.plugins.some((p) => p.via_wg)) return '';
      if (!this.routing.active) return this.$t('net.wireguard.routing_inactive');
      if (!this.routing.routing) return this.$t('net.wireguard.routing_not_ready');
      if (!this.routing.default_route) return this.$t('net.wireguard.routing_no_default_route');
      return '';
    },

    // Whether plugins can reach the internet through the tunnel with these AllowedIPs
    routesInternet() {
      return this.form.peer_allowed_ips.split(',').map((n) => n.trim()).some((n) => n === '0.0.0.0/0' || n === '::/0');
    },

    firstPeer() {
      return this.wgStatus && this.wgStatus.peers && this.wgStatus.peers.length > 0
        ? this.wgStatus.peers[0]
        : null;
    }
  },

  methods: {
    pluginTitle(plugin) {
      return plugin.title && plugin.title.startsWith('$') ? this.$t(plugin.title.slice(1)) : plugin.title;
    },

    pluginRouteHint(plugin) {
      if (!plugin.enabled) return this.$t('net.wireguard.routing_plugin_disabled');
      return plugin.via_wg ? this.$t('net.wireguard.routing_via_wg') : this.$t('net.wireguard.routing_via_default');
    },

    async loadRouting() {
      this.routingLoading = true;
      try {
        const response = await fetch('/api/net/wireguard_routing', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_load_routing');
          return;
        }
        this.routing = {
          plugins: data.plugins || [],
          active: !!data.active,
          routing: !!data.routing,
          default_route: !!data.default_route
        };
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.routingLoading = false;
      }
    },

    async onTogglePluginRouting(plugin, value) {
      this.error = '';
      this.success = '';
      this.togglingPlugin = plugin.id;
      try {
        const response = await fetch('/api/net/wireguard_routing', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ plugin: plugin.id, via_wg: value })
        });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_save_settings');
          plugin.via_wg = !value;
          return;
        }
        plugin.via_wg = !!data.via_wg;
        this.success = this.$t('net.wireguard.settings_saved');
      } catch (err) {
        this.error = this.$t('http.common.error_server');
        plugin.via_wg = !value;
      } finally {
        this.togglingPlugin = null;
      }
    },

    async loadSettings() {
      this.settingsLoading = true;
      try {
        const response = await fetch('/api/net/wireguard_settings', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_load_settings');
          return;
        }
        this.settings.active = !!data.active;
        this.settings.auto = !!data.auto;
        this.settings.skip_on_wifi = !!data.skip_on_wifi;
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.settingsLoading = false;
      }
    },

    async onToggleState(value) {
      this.error = '';
      this.success = '';
      this.togglingState = true;
      try {
        const response = await fetch('/api/net/wireguard_state', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ enabled: value })
        });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_set_state');
          this.settings.active = !value;
          return;
        }
        this.settings.active = !!data.active;
        this.success = value ? this.$t('net.wireguard.state_enabled') : this.$t('net.wireguard.state_disabled');
        this.loadStatus();
        this.loadRouting();
      } catch (err) {
        this.error = this.$t('http.common.error_server');
        this.settings.active = !value;
      } finally {
        this.togglingState = false;
      }
    },

    async onToggleAuto(value) {
      this.error = '';
      this.success = '';
      try {
        const response = await fetch('/api/net/wireguard_auto', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ enabled: value })
        });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_save_settings');
          this.settings.auto = !value;
          return;
        }
        this.settings.auto = data.auto !== undefined ? !!data.auto : value;
        this.success = this.$t('net.wireguard.settings_saved');
      } catch (err) {
        this.error = this.$t('http.common.error_server');
        this.settings.auto = !value;
      }
    },

    async onToggleSkipOnWifi(value) {
      this.error = '';
      this.success = '';
      try {
        const response = await fetch('/api/net/wireguard_skip_on_wifi', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ enabled: value })
        });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_save_settings');
          this.settings.skip_on_wifi = !value;
          return;
        }
        this.settings.skip_on_wifi = data.skip_on_wifi !== undefined ? !!data.skip_on_wifi : value;
        this.success = this.$t('net.wireguard.settings_saved');
      } catch (err) {
        this.error = this.$t('http.common.error_server');
        this.settings.skip_on_wifi = !value;
      }
    },

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

    // Fills the form from settings returned by the api; numbers come back as strings
    fillForm(settings) {
      for (const key of Object.keys(this.form)) {
        if (settings[key] !== undefined && settings[key] !== null) {
          this.form[key] = String(settings[key]);
        }
      }
    },

    async loadConfig() {
      this.loading = true;
      try {
        const response = await fetch('/api/net/wireguard_config', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_load_config');
          return;
        }
        if (!data.exists) {
          this.success = this.$t('net.wireguard.config_not_found');
          return;
        }
        this.fillForm(data.settings || {});
        this.form.private_key = '';
        this.hasPrivateKey = !!data.has_private_key;
        this.publicKey = data.public_key || '';
      } catch (err) {
        this.error = this.$t('http.common.error_server');
      } finally {
        this.loading = false;
      }
    },

    async importConfig() {
      this.error = '';
      this.success = '';
      this.importIgnored = [];
      this.importing = true;
      try {
        const response = await fetch('/api/net/wireguard_config_import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ content: this.importText })
        });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_import');
          return;
        }
        // Fields missing in the imported config are cleared, except the private key:
        // an empty one keeps the saved key
        this.fillForm(Object.fromEntries(Object.keys(this.form).map((k) => [k, (data.settings || {})[k] || ''])));
        if (data.public_key) this.publicKey = data.public_key;
        this.importIgnored = data.ignored || [];
        this.importText = '';
        this.showImport = false;
        this.success = this.$t('net.wireguard.import_done');
      } catch (err) {
        this.error = this.$t('http.common.error_server');
      } finally {
        this.importing = false;
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
          body: JSON.stringify({ settings: this.form })
        });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('net.wireguard.error_save_config');
          return;
        }
        this.success = data.restarted
          ? this.$t('net.wireguard.config_saved_restarted')
          : this.$t('net.wireguard.config_saved');
        this.importIgnored = [];
        // Reload: normalized values, the derived public key, and the routing state
        await this.loadConfig();
        this.loadStatus();
        this.loadRouting();
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
        this.form.private_key = data.private_key;
        this.publicKey = data.public_key;
        this.success = this.$t('net.wireguard.keys_generated');
      } catch (err) {
        this.error = this.$t('http.common.error_server');
      } finally {
        this.loadingKeys = false;
      }
    },

    async copyPublicKey() {
      try {
        await navigator.clipboard.writeText(this.publicKey);
        this.copiedPublic = true;
        setTimeout(() => { this.copiedPublic = false; }, 2000);
      } catch (err) {
        this.error = this.$t('net.wireguard.error_copy');
      }
    }
  },

  async mounted() {
    await Promise.all([this.loadStatus(), this.loadConfig(), this.loadSettings(), this.loadRouting()]);
  }
};

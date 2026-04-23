// Компонент страницы управления системой (сервисы и плагины)
const SystemSettingsComponent = {
  components: { ToggleSwitch, Icon },
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('http.system.title') }}</h1>
        <div v-if="loading" class="spinner spinner-sm"></div>
        <button v-else class="btn btn-icon" @click="loadData" :disabled="loading" :title="$t('http.common.refresh')">↻</button>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div v-if="!loading">
        <div
          v-for="service in services"
          :key="service.name"
          class="info-block"
          style="margin-bottom: var(--spacing-lg);"
        >
          <!-- Заголовок сервиса -->
          <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: var(--spacing-sm); margin-bottom: var(--spacing-md);">
            <div style="display: flex; align-items: center; gap: var(--spacing-md);">
              <span style="font-size: 1rem; font-weight: 600; font-family: monospace;">{{ service.name }}</span>
              <span class="status-indicator">
                <span class="status-dot" :class="{ active: service.status === 'active' }"></span>
                <span>{{ service.status }}</span>
              </span>
            </div>
            <div style="display: flex; gap: var(--spacing-sm);">
              <button
                class="btn"
                :style="service.status === 'active'
                  ? 'background: var(--color-error); color: white; padding: 6px 14px; font-size: 0.875rem;'
                  : 'background: var(--color-primary); color: white; padding: 6px 14px; font-size: 0.875rem;'"
                @click="toggleService(service)"
                :disabled="service.actionLoading"
              >
                {{ service.actionLoading ? '...' : (service.status === 'active' ? $t('http.system.stop') : $t('http.system.start')) }}
              </button>
              <button
                class="btn"
                style="background: var(--color-bg-tertiary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 6px 14px; font-size: 0.875rem;"
                @click="restartService(service)"
                :disabled="service.actionLoading"
              >
                {{ service.actionLoading ? '...' : $t('http.system.restart') }}
              </button>
            </div>
          </div>

          <!-- Плагины сервиса -->
          <div v-if="service.plugins.length > 0" style="display: flex; flex-wrap: wrap; gap: var(--spacing-sm);">
            <div
              v-for="plugin in service.plugins"
              :key="plugin.id"
              style="
                background: var(--color-bg-tertiary);
                border: 1px solid var(--color-border);
                border-radius: var(--radius-md);
                padding: var(--spacing-sm) var(--spacing-md);
                display: flex;
                align-items: center;
                gap: var(--spacing-md);
                min-width: 200px;
              "
            >
              <div style="flex: 1; min-width: 0;">
                <div style="font-size: 0.875rem; font-weight: 500; font-family: monospace; color: var(--color-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ plugin.id }}</div>
                <div style="font-size: 0.75rem; color: var(--color-text-secondary); margin-top: 2px;">{{ $t('http.system.plugin_run') }}</div>
              </div>
              <toggle-switch
                :model-value="plugin.enabled"
                :disabled="plugin.saving"
                @update:model-value="setPluginEnabled(plugin, $event)"
              ></toggle-switch>
            </div>
          </div>
          <div v-else style="color: var(--color-text-secondary); font-size: 0.875rem;">{{ $t('http.system.no_plugins') }}</div>
        </div>

      </div>
    </div>
  `,

  data() {
    return {
      services: [],
      loading: false,
      error: ''
    };
  },

  methods: {
    async loadData() {
      this.error = '';
      this.loading = true;
      try {
        const response = await fetch('/api/system/info', { credentials: 'same-origin' });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('http.system.error_load');
          return;
        }
        this.services = (result.services || []).map(s => ({
          ...s,
          actionLoading: false,
          plugins: (s.plugins || []).map(p => ({ ...p, saving: false }))
        }));
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    },

    async toggleService(service) {
      const action = service.status === 'active' ? 'stop' : 'start';
      await this.serviceAction(service, action);
    },

    async restartService(service) {
      await this.serviceAction(service, 'restart');
    },

    async serviceAction(service, action) {
      service.actionLoading = true;
      this.error = '';
      try {
        const response = await fetch('/api/system/service/action', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ service: service.name, action })
        });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('http.system.error_action');
          service.actionLoading = false;
          return;
        }
        // Небольшая задержка перед обновлением статуса
        await new Promise(r => setTimeout(r, 1200));
        await this.loadData();
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
        service.actionLoading = false;
      }
    },

    async setPluginEnabled(plugin, enabled) {
      plugin.saving = true;
      this.error = '';
      try {
        const response = await fetch('/api/system/plugin/enabled', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: plugin.id, enabled })
        });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('http.system.error_save');
          return;
        }
        plugin.enabled = enabled;
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        plugin.saving = false;
      }
    }
  },

  async mounted() {
    await this.loadData();
  }
};

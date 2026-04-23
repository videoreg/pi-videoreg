// Компонент страницы хранилища
const StorageSettingsComponent = {
  components: { ProgressBar, Icon },
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('http.storage.title') }}</h1>
        <div v-if="loading" class="spinner spinner-sm"></div>
        <button v-else class="btn btn-icon" @click="load" :title="$t('http.common.refresh')">↻</button>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div v-if="partitions.length > 0 || !loading" class="info-block">
        <div class="section-title">{{ $t('http.storage.partitions_title') }}</div>

        <div v-if="partitions.length === 0 && !loading" style="padding: var(--spacing-md) 0; color: var(--color-text-secondary);">
          {{ $t('http.storage.no_partitions') }}
        </div>

        <div v-if="partitions.length > 0" style="overflow-x: auto;">
          <table class="info-table">
            <thead>
              <tr>
                <th>{{ $t('http.storage.col_device') }}</th>
                <th>{{ $t('http.storage.col_mountpoint') }}</th>
                <th>{{ $t('http.storage.col_fs') }}</th>
                <th style="text-align: right;">{{ $t('http.storage.col_size') }}</th>
                <th style="text-align: right;">{{ $t('http.storage.col_used') }}</th>
                <th style="text-align: right;">{{ $t('http.storage.col_free') }}</th>
                <th style="min-width: 140px;">{{ $t('http.storage.col_fill') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in partitions" :key="p.mountpoint">
                <td>
                  <code class="code-inline">{{ p.device }}</code>
                </td>
                <td>
                  <code class="code-inline">{{ p.mountpoint }}</code>
                </td>
                <td style="color: var(--color-text-secondary);">{{ p.fstype }}</td>
                <td style="text-align: right; white-space: nowrap;">{{ formatBytes(p.total_bytes) }}</td>
                <td style="text-align: right; white-space: nowrap;">{{ formatBytes(p.used_bytes) }}</td>
                <td style="text-align: right; white-space: nowrap;">{{ formatBytes(p.free_bytes) }}</td>
                <td>
                  <progress-bar :value="Math.round(p.use_percent)" :variant="usageVariant(p.use_percent)" :show-label="true"></progress-bar>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  `,

  data() {
    return {
      partitions: [],
      error: '',
      loading: false
    };
  },

  methods: {
    formatBytes(bytes) {
      if (bytes == null) return '—';
      if (bytes >= 1024 * 1024 * 1024) {
        return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' ' + this.$t('http.storage.unit_gb');
      }
      if (bytes >= 1024 * 1024) {
        return (bytes / (1024 * 1024)).toFixed(0) + ' ' + this.$t('http.storage.unit_mb');
      }
      if (bytes >= 1024) {
        return (bytes / 1024).toFixed(0) + ' ' + this.$t('http.storage.unit_kb');
      }
      return bytes + ' ' + this.$t('http.storage.unit_b');
    },

    usageVariant(percent) {
      if (percent >= 90) return 'critical';
      if (percent >= 70) return 'warning';
      return 'normal';
    },

    async load() {
      this.error = '';
      this.loading = true;
      try {
        const response = await fetch('/api/stat/storage_info', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('http.storage.error_load');
          return;
        }
        this.partitions = data.partitions || [];
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

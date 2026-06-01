// Компонент страницы настроек — список ссылок на разделы
const SettingsComponent = {
  components: { Icon },
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <h1 class="page-title">{{ $t('http.settings.title') }}</h1>
      </div>

      <div class="settings-grid">
        <div
          v-for="item in items"
          :key="item.page"
          class="settings-card"
          @click="$emit('navigate', item.page)"
        >
          <icon :name="item.icon" :size="32"></icon>
          <span class="settings-card-label">{{ item.label }}</span>
        </div>
      </div>

      <div class="settings-rebuild">
        <button
          class="btn btn-ghost"
          :disabled="rebuilding"
          @click="rebuildComponents"
        >{{ rebuilding ? $t('http.settings.rebuilding') : $t('http.settings.rebuild_components') }}</button>
        <span v-if="rebuildError" class="settings-rebuild-error">{{ rebuildError }}</span>
      </div>
    </div>
  `,

  data() {
    return {
      rebuilding: false,
      rebuildError: null
    };
  },

  methods: {
    // Rebuild static/js/bundle.js from plugin manifests, then reload so the
    // freshly generated bundle is loaded by the browser.
    async rebuildComponents() {
      this.rebuilding = true;
      this.rebuildError = null;
      try {
        const response = await fetch('/api/http/bundle/rebuild', {
          method: 'POST',
          credentials: 'same-origin'
        });
        const data = await response.json();
        if (!response.ok || data.status !== 'ok') {
          this.rebuildError = data.error || this.$t('http.settings.rebuild_error');
          this.rebuilding = false;
          return;
        }
        window.location.reload();
      } catch (err) {
        this.rebuildError = this.$t('http.common.error_connection');
        this.rebuilding = false;
      }
    }
  },

  computed: {
    items() {
      const hardcoded = [
        { page: 'system',    icon: 'core',    label: this.$t('http.settings.system') },
        { page: 'users',     icon: 'users',   label: this.$t('http.settings.users') }
      ];

      // Settings entries contributed by plugin manifests, excluding pages already
      // rendered by the hardcoded list above (transitional dedup).
      const hardcodedPages = hardcoded.map((i) => i.page);
      const manifest = ((window.__vrgMenu && window.__vrgMenu.menu_settings) || [])
        .filter((i) => !hardcodedPages.includes(i.url))
        .map((i) => ({ page: i.url, icon: i.icon, label: this.$t(i.title.replace(/^\$/, '')) }));

      return [...hardcoded, ...manifest];
    }
  }
};

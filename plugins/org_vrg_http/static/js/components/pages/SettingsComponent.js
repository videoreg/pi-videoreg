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
    </div>
  `,

  computed: {
    items() {
      return [
        { page: 'camera',    icon: 'camera',  label: this.$t('http.settings.camera') },
        { page: 'wifi',      icon: 'wifi',    label: 'WiFi' },
        { page: 'modem',     icon: 'modem',   label: this.$t('http.settings.modem') },
        { page: 'wireguard', icon: 'vpn',     label: 'WireGuard' },
        { page: 'telegram',  icon: 'tg',      label: 'Telegram Bot' },
        { page: 'power',     icon: 'battery', label: this.$t('http.settings.power') },
        { page: 'sms',       icon: 'sms',     label: this.$t('http.settings.sms') },
        { page: 'storage',   icon: 'storage', label: this.$t('http.settings.storage') },
        { page: 'system',    icon: 'core',    label: this.$t('http.settings.system') },
        { page: 'users',     icon: 'users',   label: this.$t('http.settings.users') }
      ];
    }
  }
};

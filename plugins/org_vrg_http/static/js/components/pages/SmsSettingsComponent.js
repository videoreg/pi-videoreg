// Компонент настройки SMS
const SmsSettingsComponent = {
  components: {
    TabSwitch,
    Icon
  },
  emits: ['navigate'],
  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('http.sms.title') }}</h1>
      </div>

      <div class="content-section">
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

        <!-- Вкладка: Пользователи -->
        <div v-if="activeTab === 'users'">
          <div class="info-block">
            <div v-if="usersLoading" class="spinner"></div>
            <template v-else>
              <div
                v-for="user in users"
                :key="user.username"
                style="display: flex; align-items: center; gap: var(--spacing-md); margin-bottom: var(--spacing-md); max-width: 600px;"
              >
                <span style="min-width: 120px; font-weight: 500; font-size: 0.875rem; color: var(--color-text-primary);">{{ user.username }}</span>
                <input
                  type="text"
                  class="form-input"
                  v-model="user._phone"
                  placeholder="+79001234567"
                  style="flex: 1;"
                />
              </div>
              <div style="margin-top: var(--spacing-md);">
                <button
                  class="btn btn-primary"
                  :disabled="usersSaving"
                  @click="saveUsers"
                >
                  {{ usersSaving ? $t('common.saving') : $t('common.save') }}
                </button>
              </div>
            </template>
          </div>

          <div class="info-block" style="margin-top: var(--spacing-xl);">
            <div class="section-title">{{ $t('http.sms.phone_format_title') }}</div>

            <ul style="margin-left: var(--spacing-lg); color: var(--color-text-secondary);">
              <li>{{ $t('http.sms.phone_format_hint1') }}</li>
              <li>{{ $t('http.sms.phone_format_example') }}: <code style="background: var(--color-bg-tertiary); padding: 2px 6px; border-radius: var(--radius-sm);">+79001234567</code></li>
              <li>{{ $t('http.sms.phone_format_hint2') }}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  `,
  data() {
    return {
      activeTab: 'users',
      error: '',
      success: '',
      users: [],
      usersLoading: false,
      usersSaving: false
    };
  },

  computed: {
    tabs() {
      return [
        { value: 'users', label: this.$t('http.sms.tab_users') }
      ];
    }
  },

  watch: {
    activeTab() {
      this.error = '';
      this.success = '';
    }
  },
  methods: {
    async loadUsers() {
      this.usersLoading = true;
      try {
        const response = await fetch('/api/users', {
          credentials: 'same-origin'
        });
        if (!response.ok) {
          const data = await response.json();
          this.error = data.error || this.$t('http.sms.error_load_users');
          return;
        }
        const data = await response.json();
        this.users = data.users.map(u => ({
          ...u,
          _phone: u.plugin_fields?.org_vrg_sms?.phone ?? ''
        }));
      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Load users error:', err);
      } finally {
        this.usersLoading = false;
      }
    },

    async saveUsers() {
      this.error = '';
      this.success = '';
      this.usersSaving = true;
      try {
        for (const user of this.users) {
          const fields = user._phone.trim()
            ? { phone: user._phone.trim() }
            : {};
          const response = await fetch(`/api/users/${encodeURIComponent(user.username)}/plugin-fields/org_vrg_sms`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(fields)
          });
          if (!response.ok) {
            const data = await response.json();
            this.error = data.error || this.$t('http.sms.error_save_user', { username: user.username });
            return;
          }
        }
        this.success = this.$t('http.sms.users_saved');
      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Save users error:', err);
      } finally {
        this.usersSaving = false;
      }
    }
  },
  async mounted() {
    await this.loadUsers();
  }
};

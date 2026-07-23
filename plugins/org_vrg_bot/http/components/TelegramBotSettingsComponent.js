// Компонент настройки Telegram бота
const TelegramBotSettingsComponent = {
  components: {
    TabSwitch,
    Icon
  },
  emits: ['navigate'],
  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('bot.telegram.title') }}</h1>
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

        <!-- Вкладка: Настройки -->
        <div v-if="activeTab === 'settings'">
          <!-- Health indicator: shows whether the bot reaches the Telegram server -->
          <div class="info-block" style="margin-bottom: var(--spacing-lg); display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md);">
            <div style="display: flex; align-items: center; gap: var(--spacing-sm);">
              <span class="status-dot" :class="{ active: status && status.healthy }"></span>
              <div>
                <div style="font-weight: 500;">{{ statusLabel }}</div>
                <div v-if="status && status.healthy && lastOkLabel" class="form-hint" style="margin-top: 2px;">{{ lastOkLabel }}</div>
                <div v-if="status && !status.healthy && status.last_error" class="form-hint" style="margin-top: 2px;">{{ status.last_error }}</div>
              </div>
            </div>
            <button class="btn btn-icon" @click="loadStatus" :disabled="statusLoading" :title="$t('http.common.refresh')">↻</button>
          </div>

          <div class="info-block">
            <form @submit.prevent="saveConfig" style="max-width: 600px;">
              <div class="form-group">
                <label class="form-label" for="tg_bot_token">{{ $t('bot.telegram.bot_token_label') }}</label>
                <input
                  type="text"
                  id="tg_bot_token"
                  class="form-input"
                  v-model="tg_bot_token"
                  :disabled="loading"
                  placeholder="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
                  style="font-family: monospace; font-size: 0.875rem;"
                />
                <span class="form-hint">
                  {{ $t('bot.telegram.bot_token_hint') }}
                </span>
              </div>

              <div class="form-group">
                <label class="form-label" for="tg_bot_name">{{ $t('bot.telegram.bot_name_label') }}</label>
                <input
                  type="text"
                  id="tg_bot_name"
                  class="form-input"
                  v-model="tg_bot_name"
                  :disabled="loading"
                  placeholder="Videoreg"
                />
                <span class="form-hint">
                  {{ $t('bot.telegram.bot_name_hint') }}
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
            <div class="section-title">{{ $t('bot.telegram.how_to_title') }}</div>

            <ul style="margin-left: var(--spacing-lg); color: var(--color-text-secondary);">
              <li>{{ $t('bot.telegram.how_to_step1') }}</li>
              <li>{{ $t('bot.telegram.how_to_step2') }}</li>
              <li>{{ $t('bot.telegram.how_to_step3') }}</li>
              <li>{{ $t('bot.telegram.how_to_step4') }}</li>
            </ul>
          </div>
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
                  v-model="user._tgUserId"
                  placeholder="Telegram ID"
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
            <div class="section-title">{{ $t('bot.telegram.how_to_id_title') }}</div>

            <ul style="margin-left: var(--spacing-lg); color: var(--color-text-secondary);">
              <li>{{ $t('bot.telegram.how_to_id_step1') }}</li>
              <li>{{ $t('bot.telegram.how_to_id_step2') }}</li>
              <li>{{ $t('bot.telegram.how_to_id_step3') }}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  `,
  computed: {
    tabs() {
      return [
        { value: 'settings', label: this.$t('bot.telegram.tab_settings') },
        { value: 'users', label: this.$t('bot.telegram.tab_users') }
      ];
    },
    statusLabel() {
      if (!this.status) {
        return this.statusLoading ? this.$t('bot.telegram.status_checking') : this.$t('bot.telegram.status_unknown');
      }
      if (!this.status.configured) return this.$t('bot.telegram.status_not_configured');
      if (this.status.healthy) return this.$t('bot.telegram.status_healthy');
      return this.$t('bot.telegram.status_no_connection');
    },
    lastOkLabel() {
      if (!this.status || !this.status.last_ok_at) return '';
      const time = new Date(this.status.last_ok_at * 1000).toLocaleTimeString(VrgI18n.locale);
      return this.$t('bot.telegram.status_last_update', { time });
    }
  },

  data() {
    return {
      activeTab: 'settings',
      tg_bot_token: '',
      tg_bot_name: '',
      error: '',
      success: '',
      loading: false,
      users: [],
      usersLoading: false,
      usersSaving: false,
      status: null,
      statusLoading: false
    };
  },
  watch: {
    activeTab(tab) {
      this.error = '';
      this.success = '';
      if (tab === 'users' && this.users.length === 0) {
        this.loadUsers();
      }
    }
  },
  methods: {
    async loadStatus() {
      this.statusLoading = true;
      try {
        const response = await fetch('/api/bot/status', {
          method: 'GET',
          credentials: 'same-origin'
        });
        if (!response.ok) return;
        this.status = await response.json();
      } catch (err) {
        console.error('Load bot status error:', err);
      } finally {
        this.statusLoading = false;
      }
    },

    async loadConfig() {
      this.error = '';
      this.success = '';
      this.loading = true;

      try {
        const response = await fetch('/api/bot/config', {
          method: 'GET',
          credentials: 'same-origin'
        });

        if (!response.ok) {
          const data = await response.json();
          this.error = data.error || this.$t('bot.telegram.error_load');
          this.loading = false;
          return;
        }

        const data = await response.json();
        this.tg_bot_token = data.tg_bot_token || '';
        this.tg_bot_name = data.tg_bot_name || '';

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Load Telegram config error:', err);
      } finally {
        this.loading = false;
      }
    },

    async saveConfig() {
      this.error = '';
      this.success = '';

      if (!this.tg_bot_token.trim()) {
        this.error = this.$t('bot.telegram.token_empty');
        return;
      }

      this.loading = true;

      try {
        const response = await fetch('/api/bot/config', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'same-origin',
          body: JSON.stringify({
            tg_bot_token: this.tg_bot_token,
            tg_bot_name: this.tg_bot_name
          })
        });

        const data = await response.json();

        if (!response.ok) {
          this.error = data.error || this.$t('bot.telegram.error_save');
          this.loading = false;
          return;
        }

        this.success = this.$t('bot.telegram.saved');

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Save Telegram config error:', err);
      } finally {
        this.loading = false;
      }
    },

    async loadUsers() {
      this.usersLoading = true;
      try {
        const response = await fetch('/api/users', {
          credentials: 'same-origin'
        });
        if (!response.ok) {
          const data = await response.json();
          this.error = data.error || this.$t('bot.telegram.error_load_users');
          return;
        }
        const data = await response.json();
        this.users = data.users.map(u => ({
          ...u,
          _tgUserId: u.plugin_fields?.org_vrg_bot?.tg_user_id ?? ''
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
          const fields = user._tgUserId.trim()
            ? { tg_user_id: user._tgUserId.trim() }
            : {};
          const response = await fetch(`/api/users/${encodeURIComponent(user.username)}/plugin-fields/org_vrg_bot`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(fields)
          });
          if (!response.ok) {
            const data = await response.json();
            this.error = data.error || this.$t('bot.telegram.error_save_user', { username: user.username });
            return;
          }
        }
        this.success = this.$t('bot.telegram.users_saved');
      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Save users error:', err);
      } finally {
        this.usersSaving = false;
      }
    }
  },
  async mounted() {
    await this.loadConfig();
    await this.loadStatus();
  }
};

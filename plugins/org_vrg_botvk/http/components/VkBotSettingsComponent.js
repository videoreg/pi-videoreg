// VK bot settings component
const VkBotSettingsComponent = {
  components: {
    TabSwitch,
    Icon
  },
  emits: ['navigate'],
  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('botvk.vk.title') }}</h1>
      </div>

      <div class="content-section">
        <!-- Tab switch -->
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

        <!-- Tab: Settings -->
        <div v-if="activeTab === 'settings'">
          <!-- Health indicator: shows whether the bot reaches the VK server -->
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
                <label class="form-label" for="vk_bot_token">{{ $t('botvk.vk.bot_token_label') }}</label>
                <input
                  type="text"
                  id="vk_bot_token"
                  class="form-input"
                  v-model="vk_bot_token"
                  :disabled="loading"
                  placeholder="vk1.a.AbCdEf..."
                  style="font-family: monospace; font-size: 0.875rem;"
                />
                <span class="form-hint">
                  {{ $t('botvk.vk.bot_token_hint') }}
                </span>
              </div>

              <div class="form-group">
                <label class="form-label" for="vk_group_id">{{ $t('botvk.vk.group_id_label') }}</label>
                <input
                  type="text"
                  id="vk_group_id"
                  class="form-input"
                  v-model="vk_group_id"
                  :disabled="loading"
                  placeholder="123456789"
                />
                <span class="form-hint">
                  {{ $t('botvk.vk.group_id_hint') }}
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
            <div class="section-title">{{ $t('botvk.vk.how_to_title') }}</div>

            <ul style="margin-left: var(--spacing-lg); color: var(--color-text-secondary);">
              <li>{{ $t('botvk.vk.how_to_step1') }}</li>
              <li>{{ $t('botvk.vk.how_to_step2') }}</li>
              <li>{{ $t('botvk.vk.how_to_step3') }}</li>
              <li>{{ $t('botvk.vk.how_to_step4') }}</li>
            </ul>
          </div>
        </div>

        <!-- Tab: Users -->
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
                  v-model="user._vkUserId"
                  placeholder="VK ID"
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
            <div class="section-title">{{ $t('botvk.vk.how_to_id_title') }}</div>

            <ul style="margin-left: var(--spacing-lg); color: var(--color-text-secondary);">
              <li>{{ $t('botvk.vk.how_to_id_step1') }}</li>
              <li>{{ $t('botvk.vk.how_to_id_step2') }}</li>
              <li>{{ $t('botvk.vk.how_to_id_step3') }}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  `,
  computed: {
    tabs() {
      return [
        { value: 'settings', label: this.$t('botvk.vk.tab_settings') },
        { value: 'users', label: this.$t('botvk.vk.tab_users') }
      ];
    },
    statusLabel() {
      if (!this.status) {
        return this.statusLoading ? this.$t('botvk.vk.status_checking') : this.$t('botvk.vk.status_unknown');
      }
      if (!this.status.configured) return this.$t('botvk.vk.status_not_configured');
      if (this.status.healthy) return this.$t('botvk.vk.status_healthy');
      return this.$t('botvk.vk.status_no_connection');
    },
    lastOkLabel() {
      if (!this.status || !this.status.last_ok_at) return '';
      const time = new Date(this.status.last_ok_at * 1000).toLocaleTimeString(VrgI18n.locale);
      return this.$t('botvk.vk.status_last_update', { time });
    }
  },

  data() {
    return {
      activeTab: 'settings',
      vk_bot_token: '',
      vk_group_id: '',
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
        const response = await fetch('/api/botvk/status', {
          method: 'GET',
          credentials: 'same-origin'
        });
        if (!response.ok) return;
        this.status = await response.json();
      } catch (err) {
        console.error('Load VK bot status error:', err);
      } finally {
        this.statusLoading = false;
      }
    },

    async loadConfig() {
      this.error = '';
      this.success = '';
      this.loading = true;

      try {
        const response = await fetch('/api/botvk/config', {
          method: 'GET',
          credentials: 'same-origin'
        });

        if (!response.ok) {
          const data = await response.json();
          this.error = data.error || this.$t('botvk.vk.error_load');
          this.loading = false;
          return;
        }

        const data = await response.json();
        this.vk_bot_token = data.vk_bot_token || '';
        this.vk_group_id = data.vk_group_id || '';

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Load VK config error:', err);
      } finally {
        this.loading = false;
      }
    },

    async saveConfig() {
      this.error = '';
      this.success = '';

      if (!this.vk_bot_token.trim()) {
        this.error = this.$t('botvk.vk.token_empty');
        return;
      }

      if (!this.vk_group_id.trim()) {
        this.error = this.$t('botvk.vk.group_id_empty');
        return;
      }

      this.loading = true;

      try {
        const response = await fetch('/api/botvk/config', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'same-origin',
          body: JSON.stringify({
            vk_bot_token: this.vk_bot_token,
            vk_group_id: this.vk_group_id
          })
        });

        const data = await response.json();

        if (!response.ok) {
          this.error = data.error || this.$t('botvk.vk.error_save');
          this.loading = false;
          return;
        }

        this.success = this.$t('botvk.vk.saved');

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Save VK config error:', err);
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
          this.error = data.error || this.$t('botvk.vk.error_load_users');
          return;
        }
        const data = await response.json();
        this.users = data.users.map(u => ({
          ...u,
          _vkUserId: u.plugin_fields?.org_vrg_botvk?.vk_user_id ?? ''
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
          const fields = user._vkUserId.trim()
            ? { vk_user_id: user._vkUserId.trim() }
            : {};
          const response = await fetch(`/api/users/${encodeURIComponent(user.username)}/plugin-fields/org_vrg_botvk`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(fields)
          });
          if (!response.ok) {
            const data = await response.json();
            this.error = data.error || this.$t('botvk.vk.error_save_user', { username: user.username });
            return;
          }
        }
        this.success = this.$t('botvk.vk.users_saved');
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

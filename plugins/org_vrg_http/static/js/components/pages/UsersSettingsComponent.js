// Компонент страницы управления пользователями
const UsersSettingsComponent = {
  components: { Icon },
  emits: ['navigate'],
  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('http.users.title') }}</h1>
        <div v-if="loading" class="spinner spinner-sm"></div>
        <button v-else class="btn btn-icon" @click="loadUsers" :title="$t('http.common.refresh')">↻</button>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div v-if="initialLoaded">
        <button
          v-if="!showAddForm"
          class="btn btn-outline"
          style="margin-bottom: var(--spacing-lg);"
          @click="showAddForm = true"
        >
          {{ $t('http.users.add_btn') }}
        </button>

        <div v-if="showAddForm" class="info-block" style="margin-bottom: var(--spacing-lg);">
          <div class="section-title">{{ $t('http.users.add_title') }}</div>

          <div v-if="addError" class="alert alert-error">{{ addError }}</div>

          <div class="form-group">
            <label class="form-label">{{ $t('http.users.username_label') }}</label>
            <input
              class="form-input"
              v-model="newUsername"
              :disabled="addLoading"
              :placeholder="$t('http.users.username_placeholder')"
            />
          </div>

          <div class="form-group">
            <label class="form-label">{{ $t('http.users.password_label') }}</label>
            <input
              class="form-input"
              type="password"
              v-model="newPassword"
              :disabled="addLoading"
              :placeholder="$t('http.users.password_placeholder')"
            />
          </div>

          <div style="display: flex; gap: var(--spacing-sm);">
            <button class="btn btn-primary" @click="addUser" :disabled="addLoading">
              {{ addLoading ? $t('common.saving') : $t('common.save') }}
            </button>
            <button class="btn" @click="cancelAdd" :disabled="addLoading">
              {{ $t('common.cancel') }}
            </button>
          </div>
        </div>

        <div class="info-block">
          <div
            v-for="user in users"
            :key="user.username"
            style="display: flex; align-items: center; justify-content: space-between; padding: var(--spacing-sm) 0; border-bottom: 1px solid var(--color-border);"
          >
            <span>{{ user.username }}</span>
            <button
              v-if="user.username !== 'admin'"
              class="btn btn-ghost-danger"
              @click="deleteUser(user.username)"
              :disabled="loading"
            >
              {{ $t('http.users.delete_btn') }}
            </button>
          </div>
          <div
            v-if="users.length === 0"
            style="color: var(--color-text-secondary); text-align: center; padding: var(--spacing-md) 0;"
          >
            {{ $t('http.users.no_users') }}
          </div>
        </div>
      </div>
    </div>
  `,

  data() {
    return {
      users: [],
      loading: false,
      initialLoaded: false,
      showAddForm: false,
      newUsername: '',
      newPassword: '',
      addLoading: false,
      error: '',
      addError: ''
    };
  },

  methods: {
    async loadUsers() {
      this.error = '';
      this.loading = true;
      try {
        const response = await fetch('/api/users', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('http.users.error_load');
          return;
        }
        this.users = data.users || [];
        this.initialLoaded = true;
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    },

    async addUser() {
      this.addError = '';
      if (!/^[a-zA-Z0-9_-]+$/.test(this.newUsername)) {
        this.addError = this.$t('http.users.username_validation');
        return;
      }
      this.addLoading = true;
      try {
        const response = await fetch('/api/users', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: this.newUsername, password: this.newPassword })
        });
        const data = await response.json();
        if (!response.ok) {
          this.addError = data.error || this.$t('http.users.error_add');
          return;
        }
        this.showAddForm = false;
        this.newUsername = '';
        this.newPassword = '';
        await this.loadUsers();
      } catch (err) {
        this.addError = this.$t('http.common.error_connection');
      } finally {
        this.addLoading = false;
      }
    },

    async deleteUser(username) {
      this.error = '';
      this.loading = true;
      try {
        const response = await fetch('/api/users/' + username, {
          method: 'DELETE',
          credentials: 'same-origin'
        });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('http.users.error_delete');
          return;
        }
        await this.loadUsers();
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    },

    cancelAdd() {
      this.showAddForm = false;
      this.newUsername = '';
      this.newPassword = '';
      this.addError = '';
    }
  },

  async mounted() {
    await this.loadUsers();
  }
};

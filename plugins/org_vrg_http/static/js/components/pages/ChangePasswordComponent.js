// Компонент смены пароля
const ChangePasswordComponent = {
  props: {
    forced: {
      type: Boolean,
      default: false
    }
  },
  template: `
    <div v-if="forced" class="login-container">
      <div class="login-box">
        <div class="login-header">
          <h1>Videoreg</h1>
        </div>

        <p style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary); font-size: var(--font-size-sm);">
          {{ $t('http.change_pw.forced_note') }}
        </p>

        <div v-if="success" class="alert alert-success">
          {{ success }}
        </div>

        <div v-if="error" class="alert alert-error">
          {{ error }}
        </div>

        <form @submit.prevent="handleChangePassword">
          <div class="form-group">
            <label class="form-label" for="old_password_forced">{{ $t('http.change_pw.current_label') }}</label>
            <input
              type="password"
              id="old_password_forced"
              class="form-input"
              v-model="oldPassword"
              required
              :disabled="loading"
            />
          </div>

          <div class="form-group">
            <label class="form-label" for="new_password_forced">{{ $t('http.change_pw.new_label') }}</label>
            <input
              type="password"
              id="new_password_forced"
              class="form-input"
              v-model="newPassword"
              required
              minlength="6"
              :disabled="loading"
            />
            <span class="form-hint">{{ $t('http.change_pw.new_hint') }}</span>
          </div>

          <div class="form-group">
            <label class="form-label" for="confirm_password_forced">{{ $t('http.change_pw.confirm_label') }}</label>
            <input
              type="password"
              id="confirm_password_forced"
              class="form-input"
              v-model="confirmPassword"
              required
              minlength="6"
              :disabled="loading"
            />
          </div>

          <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
            {{ loading ? $t('http.change_pw.submitting') : $t('http.change_pw.submit') }}
          </button>
          <button type="button" class="btn btn-ghost btn-block btn-ghost-danger" style="margin-top: var(--spacing-sm);" :disabled="loading" @click="$emit('logout')">
            {{ $t('http.logout') }}
          </button>
        </form>
      </div>
    </div>

    <div v-else>
      <div class="page-header">
        <h1 class="page-title">{{ $t('http.change_pw.title') }}</h1>
      </div>

      <div class="content-section">
        <div v-if="success" class="alert alert-success">
          {{ success }}
        </div>

        <div v-if="error" class="alert alert-error">
          {{ error }}
        </div>

        <div class="info-block">
          <form @submit.prevent="handleChangePassword" style="max-width: 500px;">
            <div class="form-group">
              <label class="form-label" for="old_password">{{ $t('http.change_pw.current_label') }}</label>
              <input
                type="password"
                id="old_password"
                class="form-input"
                v-model="oldPassword"
                required
                :disabled="loading"
              />
            </div>

            <div class="form-group">
              <label class="form-label" for="new_password">{{ $t('http.change_pw.new_label') }}</label>
              <input
                type="password"
                id="new_password"
                class="form-input"
                v-model="newPassword"
                required
                minlength="6"
                :disabled="loading"
              />
              <span class="form-hint">{{ $t('http.change_pw.new_hint') }}</span>
            </div>

            <div class="form-group">
              <label class="form-label" for="confirm_password">{{ $t('http.change_pw.confirm_label') }}</label>
              <input
                type="password"
                id="confirm_password"
                class="form-input"
                v-model="confirmPassword"
                required
                minlength="6"
                :disabled="loading"
              />
            </div>

            <button type="submit" class="btn btn-primary" :disabled="loading">
              {{ loading ? $t('http.change_pw.submitting') : $t('http.change_pw.submit') }}
            </button>
          </form>
        </div>
      </div>
    </div>
  `,
  data() {
    return {
      oldPassword: '',
      newPassword: '',
      confirmPassword: '',
      error: '',
      success: '',
      loading: false
    };
  },
  methods: {
    async handleChangePassword() {
      this.error = '';
      this.success = '';

      // Валидация
      if (this.newPassword !== this.confirmPassword) {
        this.error = this.$t('http.change_pw.error_mismatch');
        return;
      }

      if (this.newPassword.length < 6) {
        this.error = this.$t('http.change_pw.error_too_short');
        return;
      }

      this.loading = true;

      try {
        // Токен автоматически отправляется в HTTP-only куке
        const response = await fetch('/api/auth/change-password', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'same-origin',
          body: JSON.stringify({
            old_password: this.oldPassword,
            new_password: this.newPassword
          })
        });

        const data = await response.json();

        if (!response.ok) {
          this.error = data.error || this.$t('http.change_pw.error_change');
          this.loading = false;
          return;
        }

        this.success = this.$t('http.change_pw.success');
        this.oldPassword = '';
        this.newPassword = '';
        this.confirmPassword = '';

        if (this.forced) {
          this.$emit('password-changed');
        }

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Change password error:', err);
      } finally {
        this.loading = false;
      }
    }
  }
};

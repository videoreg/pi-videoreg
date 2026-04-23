// Компонент авторизации
const LoginComponent = {
  template: `
    <div class="login-container">
      <div class="login-box">
        <div class="login-header">
          <h1>Videoreg</h1>
        </div>

        <div v-if="error" class="alert alert-error">
          {{ error }}
        </div>

        <form @submit.prevent="handleLogin" method="post">
          <div class="form-group">
            <label class="form-label" for="username">{{ $t('http.login.username') }}</label>
            <input
              type="text"
              id="username"
              name="username"
              class="form-input"
              v-model="username"
              autocomplete="username"
              required
              :disabled="loading"
            />
          </div>

          <div class="form-group">
            <label class="form-label" for="password">{{ $t('http.login.password') }}</label>
            <input
              type="password"
              id="password"
              name="password"
              class="form-input"
              v-model="password"
              autocomplete="current-password"
              required
              :disabled="loading"
            />
          </div>

          <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
            {{ loading ? $t('http.login.logging_in') : $t('http.login.title') }}
          </button>
        </form>
      </div>
    </div>
  `,
  data() {
    return {
      username: '',
      password: '',
      error: '',
      loading: false
    };
  },
  methods: {
    async handleLogin() {
      this.error = '';
      this.loading = true;

      try {
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: this.username,
            password: this.password
          })
        });

        const data = await response.json();

        if (!response.ok) {
          this.error = data.error || this.$t('http.login.error_auth');
          this.loading = false;
          return;
        }

        // Токены сохранены в HTTP-only куки сервером
        // Уведомляем родительский компонент
        this.$emit('login-success');

      } catch (err) {
        this.error = this.$t('http.common.error_server');
        console.error('Login error:', err);
      } finally {
        this.loading = false;
      }
    }
  }
};

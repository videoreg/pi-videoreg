// Главное приложение VideoReg Pi
const { createApp } = Vue;

(async () => {
  await VrgI18n.init();

  const app = createApp({
  components: {
    Icon,
    Tooltip,
    ToggleSwitch,
    ProgressBar,
    LoginComponent,
    HomeComponent,
    ChangePasswordComponent,
    SystemSettingsComponent,
    UsersSettingsComponent,
    TripsComponent,
    SettingsComponent,
    TripsMediaItem,
    // Plugin page components migrated out of org_vrg_http (provided via bundle.js
    // + the server-injected window.__vrgComponents bridge).
    ...(window.__vrgComponents || {}),
  },
  data() {
    return {
      isAuthenticated: false,
      user: null,
      currentPage: 'home',
      loading: true,
      sidebarOpen: false,
      statusData: null,
      statusLoaded: false,
      statusOffline: false,
      statusLastUpdated: null,
      _statusTimeout: null,
      _statusPolling: false,
      _popstateHandler: null,
      cameraActionLoading: null,
      powerActionLoading: null,
      keepAliveSuccess: false,
      rebootSuccess: false,
      shutdownSuccess: false,
      // System-wide first-run clock setup flag (null = not yet fetched).
      datetimeConfigured: null
    };
  },
  provide() {
    return {
      appStatusData: Vue.computed(() => this.statusData),
      appStatusOffline: Vue.computed(() => this.statusOffline),
      appStatusLastUpdated: Vue.computed(() => this.statusLastUpdated),
    };
  },
  computed: {
    mustChangePassword() {
      return this.isAuthenticated && this.user && this.user.password_changed === false;
    },

    // First-run clock setup step: shown once for the whole system (after the
    // password is changed), until completed. Persisted in the core plugin state.
    mustSetupDatetime() {
      return this.isAuthenticated && !this.mustChangePassword &&
        this.datetimeConfigured === false;
    },

    // --- Manifest-driven menu/routing (from window.__vrgMenu) ---
    manifestMenu() {
      return (window.__vrgMenu && window.__vrgMenu.menu) || [];
    },
    manifestSettings() {
      return (window.__vrgMenu && window.__vrgMenu.menu_settings) || [];
    },
    manifestSettingsUrls() {
      return this.manifestSettings.map((i) => i.url);
    },
    manifestTopUrls() {
      return this.manifestMenu.map((i) => i.url);
    },
    manifestComponentByPage() {
      const map = {};
      this.manifestMenu.concat(this.manifestSettings).forEach((i) => {
        map[i.url] = i.component;
      });
      return map;
    },
    // Main-menu items contributed by plugin manifests, excluding pages already
    // rendered by the hardcoded sidebar (transitional dedup).
    pluginMenuItems() {
      const hardcoded = [
        'home', 'trips', 'settings', 'change-password',
      ];
      return this.manifestMenu.filter((i) => !hardcoded.includes(i.url));
    },

    currentComponent() {
      if (!this.isAuthenticated) {
        return 'LoginComponent';
      }

      // Manifest-driven pages resolve first
      const manifestComponent = this.manifestComponentByPage[this.currentPage];
      if (manifestComponent) {
        return manifestComponent;
      }

      // Роутинг между страницами
      switch (this.currentPage) {
        case 'home':
          return 'HomeComponent';
        case 'change-password':
          return 'ChangePasswordComponent';
        case 'system':
          return 'SystemSettingsComponent';
        case 'users':
          return 'UsersSettingsComponent';
        case 'trips':
          return 'TripsComponent';
        case 'settings':
          return 'SettingsComponent';
        default:
          return 'HomeComponent';
      }
    },

    statusCamera() {
      return this.statusData?.camera?.video_state || 'stopped';
    },

    statusPowerSource() {
      return this.statusData?.power?.source ?? null;
    },
    statusPowerHasBattery() {
      return this.statusPowerSource?.battery_telemetry === true;
    },
    statusPowerExists() {
      return this.statusPowerSource !== null;
    },

    statusPowerCharging() {
      return this.statusData?.power?.charging === true;
    },

    statusPowerPercent() {
      return this.statusData?.power?.battery_percent ?? 0;
    },

    statusCameraLabel() {
      const labels = { record: this.$t('camera.camera.state_record'), pause: this.$t('camera.camera.state_pause'), stop: this.$t('camera.camera.state_stop') };
      return labels[this.statusCamera] || this.$t('camera.camera.state_stop');
    },

    isSettingsActive() {
      const settingsPages = ['settings', 'system', 'users', ...this.manifestSettingsUrls];
      return settingsPages.includes(this.currentPage);
    },

    statusBgImageUrl() {
      const item = this.statusData?.last_media?.item;
      if (!item) return null;
      const filename = item.type === 'video' ? item.name + '.h264' : item.name + '.jpg';
      const screenshot = item.type === 'video' && item.preview ? item.preview + '.jpg' : null;
      if (item.type === 'photo') return '/photo/' + filename.replace(/\.[^.]+$/, '');
      if (screenshot) return '/photo/' + screenshot.replace(/\.[^.]+$/, '');
      return null;
    },
  },
  methods: {
    async checkAuth() {
      try {
        // Куки автоматически отправляются браузером
        const response = await fetch('/api/auth/me', {
          credentials: 'same-origin' // Важно для отправки кук
        });
        
        if (response.ok) {
          this.user = await response.json();
          this.isAuthenticated = true;
        } else if (response.status === 401) {
          // Токен невалиден или истек, пробуем обновить
          await this.refreshToken();
        } else {
          this.isAuthenticated = false;
        }
      } catch (err) {
        console.error('Auth check error:', err);
        this.isAuthenticated = false;
      } finally {
        this.loading = false;
      }
    },
    
    async refreshToken() {
      try {
        // Refresh token тоже в HTTP-only куке
        const response = await fetch('/api/auth/refresh', {
          method: 'POST',
          credentials: 'same-origin'
        });
        
        if (response.ok) {
          // Сервер обновил куки, проверяем авторизацию снова
          const meResponse = await fetch('/api/auth/me', {
            credentials: 'same-origin'
          });
          
          if (meResponse.ok) {
            this.user = await meResponse.json();
            this.isAuthenticated = true;
          } else {
            this.isAuthenticated = false;
            this.user = null;
          }
        } else {
          // Refresh token тоже невалиден
          this.isAuthenticated = false;
          this.user = null;
        }
      } catch (err) {
        console.error('Refresh token error:', err);
        this.isAuthenticated = false;
        this.user = null;
      } finally {
        this.loading = false;
      }
    },
    
    // Load the system-wide clock-setup flag (once). On error assume configured
    // so a backend hiccup never traps the user on the onboarding screen.
    async loadDatetimeConfigured() {
      if (this.datetimeConfigured !== null) return;
      try {
        const response = await fetch('/api/core/datetime', { credentials: 'same-origin' });
        if (response.ok) {
          const result = await response.json();
          this.datetimeConfigured = result.configured === true;
        } else {
          this.datetimeConfigured = true;
        }
      } catch (err) {
        this.datetimeConfigured = true;
      }
    },

    async onLoginSuccess() {
      await this.checkAuth();

      if (this.mustChangePassword) {
        return;
      }

      // Stay on the clock setup step until it is completed.
      await this.loadDatetimeConfigured();
      if (this.mustSetupDatetime) {
        return;
      }

      this._initAfterAuth();
    },

    async onPasswordChanged() {
      if (this.user) {
        this.user = { ...this.user, password_changed: true };
      }
      // password changed → show the clock setup step if the system isn't configured.
      await this.loadDatetimeConfigured();
      if (!this.mustSetupDatetime) {
        this._initAfterAuth();
      }
    },

    async onDatetimeDone() {
      try {
        await fetch('/api/core/datetime-configured', {
          method: 'POST',
          credentials: 'same-origin'
        });
      } catch (err) {
        console.error('Failed to mark datetime configured:', err);
      }
      this.datetimeConfigured = true;
      this._initAfterAuth();
    },

    _initAfterAuth() {
      // Проверяем, есть ли параметр redirect в URL
      const urlParams = new URLSearchParams(window.location.search);
      const redirectUrl = urlParams.get('redirect');

      if (redirectUrl) {
        window.location.href = redirectUrl;
        return;
      }

      // Устанавливаем страницу из URL pathname
      const pageFromPath = this.pathToPage(window.location.pathname);
      if (pageFromPath) {
        this.currentPage = pageFromPath;
      }

      // Слушаем popstate (кнопки назад/вперёд)
      if (!this._popstateHandler) {
        this._popstateHandler = (event) => {
          const page = event.state?.page ?? this.pathToPage(window.location.pathname);
          if (page) this.currentPage = page;
        };
        window.addEventListener('popstate', this._popstateHandler);
      }

      // Запускаем опрос статуса для status bar
      this.startStatusPolling();
    },
    
    async logout() {
      // Вызываем API для очистки кук
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          credentials: 'same-origin'
        });
      } catch (err) {
        console.error('Logout error:', err);
      }
      
      this.isAuthenticated = false;
      this.user = null;
      this.currentPage = 'trips';

      // Перезагружаем страницу для очистки состояния
      window.location.href = '/';
    },
    
    pageToPath(page) {
      if (page === 'home') return '/';
      const settingsPages = ['system', 'users', ...this.manifestSettingsUrls];
      if (settingsPages.includes(page)) return '/settings/' + page;
      return '/' + page;
    },

    pathToPage(path) {
      const topPages = ['home', 'change-password', 'settings', 'trips', ...this.manifestTopUrls];
      const settingsPages = ['system', 'users', ...this.manifestSettingsUrls];
      if (path === '/') return 'home';
      if (path === '/settings') return 'settings';
      // /settings/<name>
      const settingsMatch = path.match(/^\/settings\/([^/]+)$/);
      if (settingsMatch && settingsPages.includes(settingsMatch[1])) return settingsMatch[1];
      const name = path.slice(1); // убираем ведущий "/"
      return topPages.includes(name) ? name : null;
    },

    navigate(page) {
      this.currentPage = page;
      history.pushState({ page }, '', this.pageToPath(page));
      this.closeSidebar();
    },

    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen;
    },

    closeSidebar() {
      this.sidebarOpen = false;
    },

    async cameraStart() {
      if (this.cameraActionLoading) return;
      this.cameraActionLoading = 'start';
      try {
        await fetch('/api/camera/video_start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({})
        });
        await this.fetchStatusData();
      } catch (err) {
        console.warn('Ошибка запуска камеры', err);
      } finally {
        this.cameraActionLoading = null;
      }
    },

    async cameraPause() {
      if (this.cameraActionLoading) return;
      this.cameraActionLoading = 'pause';
      try {
        await fetch('/api/camera/video_pause', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({})
        });
        await this.fetchStatusData();
      } catch (err) {
        console.warn('Ошибка паузы камеры', err);
      } finally {
        this.cameraActionLoading = null;
      }
    },

    async powerReboot() {
      if (this.powerActionLoading) return;
      if (!confirm(this.$t('http.app.confirm_reboot'))) return;
      this.powerActionLoading = 'reboot';
      try {
        await fetch('/api/power/reboot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ reason: 'manual' })
        });
        this.rebootSuccess = true;
        setTimeout(() => { this.rebootSuccess = false; }, 2000);
      } catch (err) {
        console.warn('Ошибка перезагрузки', err);
      } finally {
        this.powerActionLoading = null;
      }
    },

    async powerShutdown() {
      if (this.powerActionLoading) return;
      if (!confirm(this.$t('http.app.confirm_shutdown'))) return;
      this.powerActionLoading = 'shutdown';
      try {
        await fetch('/api/power/shutdown', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify('manual')
        });
        this.shutdownSuccess = true;
        setTimeout(() => { this.shutdownSuccess = false; }, 2000);
      } catch (err) {
        console.warn('Ошибка выключения', err);
      } finally {
        this.powerActionLoading = null;
      }
    },

    async powerKeepAlive() {
      if (this.powerActionLoading) return;
      this.powerActionLoading = 'keep_alive';
      this.keepAliveSuccess = false;
      try {
        const response = await fetch('/api/power/keep_alive', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ minutes: 5 })
        });
        if (response.ok) {
          this.keepAliveSuccess = true;
          setTimeout(() => { this.keepAliveSuccess = false; }, 2000);
        } else {
          console.warn('Ошибка keep_alive', await response.text());
        }
      } catch (err) {
        console.warn('Ошибка keep_alive', err);
      } finally {
        this.powerActionLoading = null;
      }
    },

    async fetchStatusData() {
      try {
        const response = await fetch('/api/statusbar/status', { credentials: 'same-origin' });
        if (response.ok) {
          this.statusData = await response.json();
          this.statusLoaded = true;
          this.statusOffline = false;
          this.statusLastUpdated = new Date();
        } else {
          this.statusOffline = true;
        }
      } catch (err) {
        this.statusOffline = true;
      } finally {
        if (this._statusPolling) {
          this._statusTimeout = setTimeout(() => this.fetchStatusData(), 5000);
        }
      }
    },

    startStatusPolling() {
      this._statusPolling = true;
      this.fetchStatusData();
    },

    stopStatusPolling() {
      this._statusPolling = false;
      if (this._statusTimeout) {
        clearTimeout(this._statusTimeout);
        this._statusTimeout = null;
      }
    }
  },
  async mounted() {
    console.log('VideoReg Pi запущен');
    await this.checkAuth();

    if (this.isAuthenticated && !this.mustChangePassword) {
      await this.loadDatetimeConfigured();
      if (!this.mustSetupDatetime) {
        this._initAfterAuth();
      }
    }
  },

  beforeUnmount() {
    this.stopStatusPolling();
    if (this._popstateHandler) {
      window.removeEventListener('popstate', this._popstateHandler);
      this._popstateHandler = null;
    }
  }
  });

  app.component('Shimmer', Shimmer);

  app.config.globalProperties.$t = (key, vars) => VrgI18n.t(key, vars);
  app.config.globalProperties.$p = (key, n, vars) => VrgI18n.p(key, n, vars);

  app.mount('#app');
})();

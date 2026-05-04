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
    WireguardSettingsComponent,
    ModemSettingsComponent,
    TelegramBotSettingsComponent,
    SmsSettingsComponent,
    WiFiSettingsComponent,
    ChangePasswordComponent,
    CameraSettingsComponent,
    PowerSettingsComponent,
    MediaFeedComponent,
    MediaFaveComponent,
    StorageSettingsComponent,
    SystemSettingsComponent,
    StatComponent,
    UsersSettingsComponent,
    SmsInboxComponent,
    GpsTracksComponent,
    TripsComponent,
    SettingsComponent,
    TripsMediaItem
  },
  data() {
    return {
      isAuthenticated: false,
      user: null,
      currentPage: 'trips',
      loading: true,
      sidebarOpen: false,
      statusData: null,
      statusLastMedia: null,
      statusLoaded: false,
      statusOffline: false,
      statusLastUpdated: null,
      vrgStateCollapsed: localStorage.getItem('vrgStateCollapsed') === '1',
      _statusTimeout: null,
      _statusPolling: false,
      _popstateHandler: null,
      cameraActionLoading: null,
      powerActionLoading: null,
      keepAliveSuccess: false,
      rebootSuccess: false,
      shutdownSuccess: false,
      takingPhoto: false,
      takenPhotos: [],
      takingShortVideo: false,
      takenShortVideos: []
    };
  },
  computed: {
    mustChangePassword() {
      return this.isAuthenticated && this.user && this.user.password_changed === false;
    },

    currentComponent() {
      if (!this.isAuthenticated) {
        return 'LoginComponent';
      }
      
      // Роутинг между страницами
      switch (this.currentPage) {
        case 'home':
          return 'HomeComponent';
        case 'wireguard':
          return 'WireguardSettingsComponent';
        case 'modem':
          return 'ModemSettingsComponent';
        case 'telegram':
          return 'TelegramBotSettingsComponent';
        case 'sms':
          return 'SmsSettingsComponent';
        case 'wifi':
          return 'WiFiSettingsComponent';
        case 'change-password':
          return 'ChangePasswordComponent';
        case 'camera':
          return 'CameraSettingsComponent';
        case 'power':
          return 'PowerSettingsComponent';
        case 'media-feed':
          return 'MediaFeedComponent';
        case 'media-fave':
          return 'MediaFaveComponent';
        case 'storage':
          return 'StorageSettingsComponent';
        case 'system':
          return 'SystemSettingsComponent';
        case 'stat':
          return 'StatComponent';
        case 'users':
          return 'UsersSettingsComponent';
        case 'sms-inbox':
          return 'SmsInboxComponent';
        case 'gps-tracks':
          return 'GpsTracksComponent';
        case 'trips':
          return 'TripsComponent';
        case 'settings':
          return 'SettingsComponent';
        default:
          return 'TripsComponent';
      }
    },

    statusCamera() {
      return this.statusData?.camera?.video_state || 'stopped';
    },

    statusWifiAp() {
      return this.statusData?.connections?.ap?.enabled === true;
    },

    statusWifiConnected() {
      return this.statusData?.connections?.wifi?.enabled === true;
    },

    statusModemExists() {
      return this.statusData?.modem?.connected === true;
    },

    statusModemConnected() {
      return this.statusData?.connections?.modem?.enabled === true;
    },

    statusWireguard() {
      return this.statusData?.wireguard?.active === true;
    },

    statusPowerExists() {
      return this.statusData?.power != null && this.statusData.power.battery_percent != null;
    },

    statusPowerCharging() {
      return this.statusData?.power?.charging === true;
    },

    statusPowerPercent() {
      return this.statusData?.power?.battery_percent ?? 0;
    },

    statusCameraLabel() {
      const labels = { record: this.$t('http.camera.state_record'), pause: this.$t('http.camera.state_pause'), stop: this.$t('http.camera.state_stop') };
      return labels[this.statusCamera] || this.$t('http.camera.state_stop');
    },

    isSettingsActive() {
      const settingsPages = ['settings', 'camera', 'wifi', 'modem', 'wireguard', 'telegram', 'power', 'sms', 'storage', 'system', 'users'];
      return settingsPages.includes(this.currentPage);
    },

    statusLastUpdatedLabel() {
      if (!this.statusLastUpdated) return null;
      return this.statusLastUpdated.toLocaleTimeString(VrgI18n.locale, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    },

    statusLastMediaItem() {
      const item = (this.statusData?.last_media ?? this.statusLastMedia)?.item;
      if (!item) return null;
      const result = {
        type: item.type,
        filename: item.type === 'video' ? item.name + '.h264' : item.name + '.jpg',
        date: item.datetime,
      };
      if (item.type === 'video' && item.preview) {
        result.screenshot = item.preview + '.jpg';
      }
      return result;
    },

    statusLastMediaReady() {
      return (this.statusData?.last_media ?? this.statusLastMedia)?.item?.ready === true;
    },

    gpsLocation() {
      const gps = this.statusData?.location?.gps;
      const lat = parseFloat(gps?.latitude);
      const lng = parseFloat(gps?.longitude);
      if (!isFinite(lat) || !isFinite(lng)) return null;
      return {
        url: `https://yandex.ru/maps/?mode=search&text=${lat}%2C${lng}`,
        label: `GPS: ${lat.toFixed(2)}, ${lng.toFixed(2)}`,
        coords: `${lat}, ${lng}`,
      };
    },

    lbsLocation() {
      const lbs = this.statusData?.location?.lbs;
      const lat = parseFloat(lbs?.latitude);
      const lng = parseFloat(lbs?.longitude);
      if (!isFinite(lat) || !isFinite(lng)) return null;
      return {
        url: `https://yandex.ru/maps/?mode=search&text=${lat}%2C${lng}`,
        label: `LBS: ${lat.toFixed(2)}, ${lng.toFixed(2)}`,
        coords: `${lat}, ${lng}`,
      };
    },
  },
  methods: {
    async copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text);
      } catch (e) {
        // fallback for non-secure context
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
      }
    },

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
    
    async onLoginSuccess() {
      await this.checkAuth();

      if (this.mustChangePassword) {
        return;
      }

      this._initAfterAuth();
    },

    onPasswordChanged() {
      if (this.user) {
        this.user = { ...this.user, password_changed: true };
      }
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
      if (page === 'trips') return '/';
      const settingsPages = ['camera', 'wifi', 'modem', 'wireguard', 'telegram', 'power', 'sms', 'storage', 'system', 'users'];
      if (settingsPages.includes(page)) return '/settings/' + page;
      return '/' + page;
    },

    pathToPage(path) {
      const topPages = ['home', 'change-password', 'settings', 'stat', 'sms-inbox', 'gps-tracks', 'trips', 'media-feed', 'media-fave'];
      const settingsPages = ['camera', 'wifi', 'modem', 'wireguard', 'telegram', 'power', 'sms', 'storage', 'system', 'users'];
      if (path === '/') return 'trips';
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
          body: JSON.stringify({})
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
          body: JSON.stringify({})
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

    _nameToDatetime(name) {
      const [date, time] = name.split('_');
      return date + 'T' + time.replace(/-/g, ':');
    },

    async takePhoto(mode) {
      if (this.takingPhoto) return;
      this.takingPhoto = true;
      try {
        const body = mode ? { mode } : {};
        const response = await fetch('/api/camera/photo', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        const data = await response.json();
        if (!response.ok) return;
        const datetime = this._nameToDatetime(data.name);
        this.takenPhotos = [{ type: 'photo', filename: data.name + '.jpg', date: datetime }, ...this.takenPhotos];
      } catch (err) {
        console.warn('Ошибка съёмки', err);
      } finally {
        this.takingPhoto = false;
      }
    },

    async takeShortVideo() {
      if (this.takingShortVideo) return;
      this.takingShortVideo = true;
      try {
        const response = await fetch('/api/camera/short_video', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        const data = await response.json();
        if (!response.ok) return;
        const datetime = this._nameToDatetime(data.name);
        this.takenShortVideos = [{ type: 'video', filename: data.name + '.mp4', date: datetime }, ...this.takenShortVideos];
      } catch (err) {
        console.warn('Ошибка съёмки видео', err);
      } finally {
        this.takingShortVideo = false;
      }
    },

    async fetchStatusData() {
      try {
        const response = await fetch('/api/dashboard/status', { credentials: 'same-origin' });
        if (response.ok) {
          this.statusData = await response.json();
          if (this.statusData?.last_media) {
            this.statusLastMedia = this.statusData.last_media;
          }
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
  watch: {
    vrgStateCollapsed(val) {
      localStorage.setItem('vrgStateCollapsed', val ? '1' : '0');
    }
  },
  async mounted() {
    console.log('VideoReg Pi запущен');
    await this.checkAuth();

    if (this.isAuthenticated && !this.mustChangePassword) {
      this._initAfterAuth();
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

  app.config.globalProperties.$t = (key, vars) => VrgI18n.t(key, vars);
  app.config.globalProperties.$p = (key, n, vars) => VrgI18n.p(key, n, vars);

  app.mount('#app');
})();

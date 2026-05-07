// Компонент страницы камеры
const CameraSettingsComponent = {
  components: { TabSwitch, Icon },
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('http.camera.title') }}</h1>
        <div v-if="loading || loadingSettings" class="spinner spinner-sm"></div>
        <button v-else class="btn btn-icon" @click="loadInfo(); loadSettings();" :disabled="loading || loadingSettings" :title="$t('http.common.refresh')">↻</button>
      </div>

      <template v-if="!loading && !loadingSettings">

      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="success" class="alert alert-success">{{ success }}</div>

      <tab-switch v-model="activeTab" :tabs="tabs" style="margin-bottom: var(--spacing-lg);"></tab-switch>

      <!-- Вкладка: Информация -->
      <div v-show="activeTab === 'info'">
        <div style="display: flex; gap: var(--spacing-sm); margin-bottom: var(--spacing-lg);">
          <button class="btn btn-outline" @click="videoStart" :disabled="actionLoading">
            {{ actionLoading === 'start' ? $t('http.camera.starting') : $t('http.camera.start') }}
          </button>
          <button class="btn btn-outline" @click="videoPause" :disabled="actionLoading">
            {{ actionLoading === 'pause' ? $t('http.camera.pausing') : $t('http.camera.pause') }}
          </button>
        </div>

        <div class="info-block">
          <div class="section-title">{{ $t('http.camera.info_title') }}</div>

          <div class="info-rows">
            <div class="info-row">
              <span class="info-label">{{ $t('http.camera.model_label') }}</span>
              <strong>{{ cameraModel }}</strong>
            </div>

            <div class="info-row">
              <span class="info-label">{{ $t('http.camera.record_status') }}</span>
              <span class="status-indicator">
                <span class="status-dot" :class="{ active: videoState === 'record' }"></span>
                <span>{{ videoStateLabel }}</span>
              </span>
            </div>

            <div class="info-row">
              <span class="info-label">{{ $t('http.camera.mode_label') }}</span>
              <strong>{{ info?.camera_mode_str || '—' }}</strong>
            </div>

            <div class="info-row">
              <span class="info-label">{{ $t('http.camera.resolution_label') }}</span>
              <strong>{{ info?.video_width && info?.video_height ? info.video_width + '×' + info.video_height : '—' }}</strong>
            </div>

            <div class="info-row">
              <span class="info-label">{{ $t('http.camera.fps_label') }}</span>
              <strong>{{ info?.fps || '—' }}</strong>
            </div>

            <div class="info-row">
              <span class="info-label">{{ $t('http.camera.bitrate_label') }}</span>
              <strong>{{ info?.bitrate ? (info.bitrate / 1000000) + ' ' + $t('http.camera.bitrate_unit') : '—' }}</strong>
            </div>
          </div>
        </div>
      </div>

      <!-- Вкладка: Настройки -->
      <div v-show="activeTab === 'settings'">
        <div class="info-block">
          <div style="max-width: 600px;">

            <!-- Режим камеры -->
            <div class="form-group">
              <label class="form-label">{{ $t('http.camera.mode_select_label') }}</label>
              <div v-if="modes.length === 0" class="info-block" style="margin-top: var(--spacing-xs);">
                <span style="color: var(--color-text-secondary);">{{ $t('http.camera.modes_unavailable') }}</span>
                <span v-if="settings.camera_mode_str">
                  {{ $t('http.camera.current_mode') }} <strong>{{ settings.camera_mode_str }}</strong>
                </span>
              </div>
              <select
                v-else
                class="form-input"
                v-model="selectedMode"
                :disabled="saving"
              >
                <option
                  v-for="mode in modes"
                  :key="mode.mode_str"
                  :value="mode"
                >{{ mode.label }}</option>
              </select>
            </div>

            <!-- Разрешение выходного файла -->
            <div class="form-group">
              <label class="form-label">{{ $t('http.camera.resolution_select') }}</label>
              <select
                class="form-input"
                v-model="selectedResolution"
                :disabled="saving"
              >
                <option
                  v-for="res in resolutions"
                  :key="res.width + 'x' + res.height"
                  :value="res"
                >{{ res.label }}</option>
              </select>
            </div>

            <!-- FPS -->
            <div class="form-group">
              <label class="form-label">{{ $t('http.camera.fps_label') }}</label>
              <select
                class="form-input"
                v-model="settings.fps"
                :disabled="saving"
              >
                <option :value="15">15</option>
                <option :value="30">30</option>
              </select>
            </div>

            <!-- Битрейт -->
            <div class="form-group">
              <label class="form-label">{{ $t('http.camera.bitrate_label') }}</label>
              <select
                class="form-input"
                v-model="settings.bitrate"
                :disabled="saving"
              >
                <option :value="2000000">2 {{ $t('http.camera.bitrate_unit') }}</option>
                <option :value="3000000">3 {{ $t('http.camera.bitrate_unit') }}</option>
                <option :value="4000000">4 {{ $t('http.camera.bitrate_unit') }}</option>
                <option :value="5000000">5 {{ $t('http.camera.bitrate_unit') }}</option>
              </select>
            </div>

            <!-- Горизонтальное отражение -->
            <div class="form-group">
              <label class="form-label">{{ $t('http.camera.hflip_label') }}</label>
              <select
                class="form-input"
                v-model="settings.hflip"
                :disabled="saving"
              >
                <option :value="false">{{ $t('http.camera.flip_default') }}</option>
                <option :value="true">{{ $t('http.camera.flip_mirror') }}</option>
              </select>
            </div>

            <!-- Вертикальное отражение -->
            <div class="form-group">
              <label class="form-label">{{ $t('http.camera.vflip_label') }}</label>
              <select
                class="form-input"
                v-model="settings.vflip"
                :disabled="saving"
              >
                <option :value="false">{{ $t('http.camera.flip_default') }}</option>
                <option :value="true">{{ $t('http.camera.flip_mirror') }}</option>
              </select>
            </div>

            <!-- Скриншоты -->
            <div class="form-group">
              <label class="form-label">{{ $t('http.camera.screenshot_label') }}</label>
              <select
                class="form-input"
                v-model="settings.screenshot"
                :disabled="saving"
              >
                <option :value="true">{{ $t('http.camera.screenshot_enabled') }}</option>
                <option :value="false">{{ $t('http.camera.screenshot_disabled') }}</option>
              </select>
            </div>

            <button class="btn btn-primary" @click="saveSettings" :disabled="saving">
              {{ saving ? $t('common.saving') : $t('common.save') }}
            </button>
          </div>
        </div>

        <!-- Live stream settings -->
        <div class="info-block" style="margin-top: var(--spacing-lg);">
          <div class="section-title">{{ $t('http.live.settings_title') }}</div>
          <div style="max-width: 600px;">

            <!-- Stream camera mode -->
            <div class="form-group">
              <label class="form-label">{{ $t('http.live.mode_select_label') }}</label>
              <div v-if="modes.length === 0" class="info-block" style="margin-top: var(--spacing-xs);">
                <span style="color: var(--color-text-secondary);">{{ $t('http.camera.modes_unavailable') }}</span>
                <span v-if="streamSettings.stream_camera_mode_str">
                  {{ $t('http.camera.current_mode') }} <strong>{{ streamSettings.stream_camera_mode_str }}</strong>
                </span>
              </div>
              <select
                v-else
                class="form-input"
                v-model="selectedStreamMode"
                :disabled="savingStream"
              >
                <option
                  v-for="mode in modes"
                  :key="mode.mode_str"
                  :value="mode"
                >{{ mode.label }}</option>
              </select>
            </div>

            <!-- Stream resolution -->
            <div class="form-group">
              <label class="form-label">{{ $t('http.live.resolution_select') }}</label>
              <select
                class="form-input"
                v-model="selectedStreamResolution"
                :disabled="savingStream"
              >
                <option
                  v-for="res in resolutions"
                  :key="res.width + 'x' + res.height"
                  :value="res"
                >{{ res.label }}</option>
              </select>
            </div>

            <button class="btn btn-primary" @click="saveStreamSettings" :disabled="savingStream">
              {{ savingStream ? $t('common.saving') : $t('common.save') }}
            </button>
          </div>
        </div>

      </div>

      </template>
    </div>
  `,

  data() {
    return {
      activeTab: 'info',

      // Информация
      info: null,
      loading: false,

      // Настройки
      modes: [],
      selectedMode: null,
      resolutions: [
        { width: 640, height: 480, label: '640×480' },
        { width: 1280, height: 720, label: '1280×720' },
        { width: 1920, height: 1080, label: '1920×1080' }
      ],
      selectedResolution: null,
      settings: {
        camera_mode_str: '',
        video_width: null,
        video_height: null,
        fps: 15,
        bitrate: 4000000,
        hflip: false,
        vflip: false,
        screenshot: true
      },
      loadingSettings: false,
      saving: false,

      // Stream settings
      streamSettings: {
        stream_camera_mode_str: '',
        stream_video_width: 1280,
        stream_video_height: 720,
      },
      selectedStreamMode: null,
      selectedStreamResolution: null,
      savingStream: false,

      error: '',
      success: '',
      actionLoading: null
    };
  },

  computed: {
    tabs() {
      return [
        { value: 'info', label: this.$t('http.camera.info_tab') },
        { value: 'settings', label: this.$t('http.camera.settings_tab') }
      ];
    },

    cameraModel() {
      if (!this.info) return '—';
      return this.info.model || this.$t('http.camera.no_camera');
    },

    videoState() {
      return this.info ? this.info.video_state : null;
    },

    videoStateLabel() {
      const labels = {
        record: this.$t('http.camera.state_record'),
        pause: this.$t('http.camera.state_pause'),
        stop: this.$t('http.camera.state_stop')
      };
      return labels[this.videoState] || '—';
    }
  },

  watch: {
    selectedMode(mode) {
      if (mode) {
        this.settings.camera_mode_str = mode.mode_str;
      }
    },
    selectedResolution(res) {
      if (res) {
        this.settings.video_width = res.width;
        this.settings.video_height = res.height;
      }
    },
    selectedStreamMode(mode) {
      if (mode) {
        this.streamSettings.stream_camera_mode_str = mode.mode_str;
      }
    },
    selectedStreamResolution(res) {
      if (res) {
        this.streamSettings.stream_video_width = res.width;
        this.streamSettings.stream_video_height = res.height;
      }
    }
  },

  methods: {
    async loadInfo() {
      this.error = '';
      this.loading = true;
      try {
        const response = await fetch('/api/camera/info', { credentials: 'same-origin' });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('http.camera.error_load');
          return;
        }
        this.info = result;
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    },

    async loadSettings() {
      this.error = '';
      this.loadingSettings = true;
      try {
        const [infoRes, modesRes] = await Promise.all([
          fetch('/api/camera/info', { credentials: 'same-origin' }),
          fetch('/api/camera/modes', { credentials: 'same-origin' })
        ]);

        const infoData = await infoRes.json();
        if (!infoRes.ok) {
          this.error = infoData.error || this.$t('http.camera.error_load_settings');
          return;
        }

        const modesData = await modesRes.json();

        this.info = infoData;
        this.settings.camera_mode_str = infoData.camera_mode_str || '';
        this.settings.video_width = infoData.video_width || null;
        this.settings.video_height = infoData.video_height || null;
        this.settings.fps = infoData.fps || 15;
        this.settings.bitrate = infoData.bitrate || 4000000;
        this.settings.hflip = infoData.hflip || false;
        this.settings.vflip = infoData.vflip || false;
        this.settings.screenshot = infoData.screenshot !== undefined ? infoData.screenshot : true;

        this.modes = (modesData.modes) || [];

        if (this.modes.length > 0) {
          const current = this.modes.find(m => m.mode_str === this.settings.camera_mode_str);
          this.selectedMode = current || this.modes[0];
        }

        const currentRes = this.resolutions.find(
          r => r.width === this.settings.video_width && r.height === this.settings.video_height
        );
        this.selectedResolution = currentRes || this.resolutions[0];

        this.streamSettings.stream_camera_mode_str = infoData.stream_camera_mode_str || '';
        this.streamSettings.stream_video_width = infoData.stream_video_width || 1280;
        this.streamSettings.stream_video_height = infoData.stream_video_height || 720;

        if (this.modes.length > 0) {
          const currentStream = this.modes.find(m => m.mode_str === this.streamSettings.stream_camera_mode_str);
          this.selectedStreamMode = currentStream || this.modes[0];
        }

        const currentStreamRes = this.resolutions.find(
          r => r.width === this.streamSettings.stream_video_width && r.height === this.streamSettings.stream_video_height
        );
        this.selectedStreamResolution = currentStreamRes || this.resolutions.find(r => r.width === 1280) || this.resolutions[0];
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loadingSettings = false;
      }
    },

    async videoStart() {
      this.error = '';
      this.success = '';
      this.actionLoading = 'start';
      try {
        const response = await fetch('/api/camera/video_start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({})
        });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('http.camera.error_start');
          return;
        }
        this.success = this.$t('http.camera.record_started');
        await this.loadInfo();
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.actionLoading = null;
      }
    },

    async videoPause() {
      this.error = '';
      this.success = '';
      this.actionLoading = 'pause';
      try {
        const response = await fetch('/api/camera/video_pause', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({})
        });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('http.camera.error_pause');
          return;
        }
        this.success = this.$t('http.camera.record_paused');
        await this.loadInfo();
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.actionLoading = null;
      }
    },

    async saveSettings() {
      this.error = '';
      this.success = '';
      this.saving = true;
      try {
        const body = {
          camera_mode_str: this.settings.camera_mode_str,
          video_width: this.settings.video_width,
          video_height: this.settings.video_height,
          fps: this.settings.fps,
          bitrate: this.settings.bitrate,
          hflip: this.settings.hflip,
          vflip: this.settings.vflip,
          screenshot: this.settings.screenshot
        };
        const response = await fetch('/api/camera/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify(body)
        });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('http.camera.error_save');
          return;
        }
        this.success = this.$t('http.camera.settings_saved');
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.saving = false;
      }
    },

    async saveStreamSettings() {
      this.error = '';
      this.success = '';
      this.savingStream = true;
      try {
        const body = {
          stream_camera_mode_str: this.streamSettings.stream_camera_mode_str,
          stream_video_width: this.streamSettings.stream_video_width,
          stream_video_height: this.streamSettings.stream_video_height,
        };
        const response = await fetch('/api/camera/stream_settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify(body)
        });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('http.live.error_save');
          return;
        }
        this.success = this.$t('http.camera.settings_saved');
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.savingStream = false;
      }
    }
  },

  async mounted() {
    await Promise.all([this.loadInfo(), this.loadSettings()]);
  }
};

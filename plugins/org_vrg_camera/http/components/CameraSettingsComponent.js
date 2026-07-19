// Компонент страницы камеры
const CameraSettingsComponent = {
  components: { TabSwitch, Icon },
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('camera.camera.title') }}</h1>
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
            {{ actionLoading === 'start' ? $t('camera.camera.starting') : $t('camera.camera.start') }}
          </button>
          <button class="btn btn-outline" @click="videoPause" :disabled="actionLoading">
            {{ actionLoading === 'pause' ? $t('camera.camera.pausing') : $t('camera.camera.pause') }}
          </button>
        </div>

        <div class="info-block">
          <div class="section-title">{{ $t('camera.camera.info_title') }}</div>

          <div class="info-rows">
            <div class="info-row">
              <span class="info-label">{{ $t('camera.camera.model_label') }}</span>
              <strong>{{ cameraModel }}</strong>
            </div>

            <div class="info-row">
              <span class="info-label">{{ $t('camera.camera.record_status') }}</span>
              <span class="status-indicator">
                <span class="status-dot" :class="{ active: videoState === 'record' }"></span>
                <span>{{ videoStateLabel }}</span>
              </span>
            </div>

            <div class="info-row">
              <span class="info-label">{{ $t('camera.camera.thermal_label') }}</span>
              <strong>{{ thermalStatusLabel }}</strong>
            </div>

            <div class="info-row">
              <span class="info-label">{{ $t('camera.camera.mode_label') }}</span>
              <strong>{{ info?.camera_mode_str || '—' }}</strong>
            </div>

            <div class="info-row">
              <span class="info-label">{{ $t('camera.camera.resolution_label') }}</span>
              <strong>{{ info?.video_width && info?.video_height ? info.video_width + '×' + info.video_height : '—' }}</strong>
            </div>

            <div class="info-row">
              <span class="info-label">{{ $t('camera.camera.fps_label') }}</span>
              <strong>{{ info?.fps || '—' }}</strong>
            </div>

            <div class="info-row">
              <span class="info-label">{{ $t('camera.camera.bitrate_label') }}</span>
              <strong>{{ info?.bitrate ? (info.bitrate / 1000000) + ' ' + $t('camera.camera.bitrate_unit') : '—' }}</strong>
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
              <label class="form-label">{{ $t('camera.camera.mode_select_label') }}</label>
              <div v-if="modes.length === 0" class="info-block" style="margin-top: var(--spacing-xs);">
                <span style="color: var(--color-text-secondary);">{{ $t('camera.camera.modes_unavailable') }}</span>
                <span v-if="settings.camera_mode_str">
                  {{ $t('camera.camera.current_mode') }} <strong>{{ settings.camera_mode_str }}</strong>
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
              <label class="form-label">{{ $t('camera.camera.resolution_select') }}</label>
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
              <label class="form-label">{{ $t('camera.camera.fps_label') }}</label>
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
              <label class="form-label">{{ $t('camera.camera.bitrate_label') }}</label>
              <select
                class="form-input"
                v-model="settings.bitrate"
                :disabled="saving"
              >
                <option :value="2000000">2 {{ $t('camera.camera.bitrate_unit') }}</option>
                <option :value="3000000">3 {{ $t('camera.camera.bitrate_unit') }}</option>
                <option :value="4000000">4 {{ $t('camera.camera.bitrate_unit') }}</option>
                <option :value="5000000">5 {{ $t('camera.camera.bitrate_unit') }}</option>
              </select>
            </div>

            <!-- Горизонтальное отражение -->
            <div class="form-group">
              <label class="form-label">{{ $t('camera.camera.hflip_label') }}</label>
              <select
                class="form-input"
                v-model="settings.hflip"
                :disabled="saving"
              >
                <option :value="false">{{ $t('camera.camera.flip_default') }}</option>
                <option :value="true">{{ $t('camera.camera.flip_mirror') }}</option>
              </select>
            </div>

            <!-- Вертикальное отражение -->
            <div class="form-group">
              <label class="form-label">{{ $t('camera.camera.vflip_label') }}</label>
              <select
                class="form-input"
                v-model="settings.vflip"
                :disabled="saving"
              >
                <option :value="false">{{ $t('camera.camera.flip_default') }}</option>
                <option :value="true">{{ $t('camera.camera.flip_mirror') }}</option>
              </select>
            </div>

            <!-- Скриншоты -->
            <div class="form-group">
              <label class="form-label">{{ $t('camera.camera.screenshot_label') }}</label>
              <select
                class="form-input"
                v-model="settings.screenshot"
                :disabled="saving"
              >
                <option :value="true">{{ $t('camera.camera.screenshot_enabled') }}</option>
                <option :value="false">{{ $t('camera.camera.screenshot_disabled') }}</option>
              </select>
            </div>

            <button class="btn btn-primary" @click="saveSettings" :disabled="saving">
              {{ saving ? $t('common.saving') : $t('common.save') }}
            </button>
          </div>
        </div>

        <!-- Storage: video files limit -->
        <div class="info-block" style="margin-top: var(--spacing-lg);">
          <div class="section-title">{{ $t('camera.camera.storage_title') }}</div>
          <div style="max-width: 600px;">
            <div class="form-group" style="margin-bottom: var(--spacing-sm);">
              <label class="form-label">{{ $t('camera.camera.files_limit_label') }}</label>
              <input
                type="number"
                class="form-input"
                v-model.number="filesLimit"
                :min="1"
                :max="maxAllowedFiles || undefined"
                step="1"
                :disabled="savingLimit"
              />
              <div style="margin-top: var(--spacing-xs); color: var(--color-text-secondary); font-size: 0.875rem;">
                {{ $t('camera.camera.files_limit_desc') }}
              </div>
            </div>

            <!-- Smart counter: estimated footprint, recomputed on the frontend -->
            <div v-if="storageStats" class="info-block" style="margin-top: var(--spacing-xs); padding: var(--spacing-sm) var(--spacing-md);">
              <div style="font-size: 1.1rem; font-weight: 600;" :style="{ color: limitExceeded ? 'var(--color-error)' : 'var(--color-text)' }">
                {{ $t('camera.camera.files_limit_estimate', { size: formatBytes(estimatedBytes) }) }}
              </div>
              <div style="margin-top: var(--spacing-xs); color: var(--color-text-secondary); font-size: 0.875rem;">
                {{ storageStats.h264_count > 0
                    ? $t('camera.camera.files_limit_avg_measured', { size: formatBytes(avgFileBytes), count: storageStats.h264_count })
                    : $t('camera.camera.files_limit_avg_estimated', { size: formatBytes(avgFileBytes) }) }}
              </div>
              <div v-if="maxAllowedFiles" style="margin-top: var(--spacing-xs); font-size: 0.875rem;"
                   :style="{ color: limitExceeded ? 'var(--color-error)' : 'var(--color-text-secondary)' }">
                {{ $t('camera.camera.files_limit_max', { max: maxAllowedFiles }) }}
              </div>
            </div>

            <div v-if="limitExceeded" class="alert alert-error" style="margin-top: var(--spacing-sm);">
              {{ $t('camera.camera.files_limit_exceeded', { max: maxAllowedFiles }) }}
            </div>

            <button class="btn btn-primary" style="margin-top: var(--spacing-md);"
                    @click="saveFilesLimit" :disabled="savingLimit || limitExceeded || !isLimitValid">
              {{ savingLimit ? $t('common.saving') : $t('common.save') }}
            </button>
          </div>
        </div>

        <!-- Live stream settings -->
        <div class="info-block" style="margin-top: var(--spacing-lg);">
          <div class="section-title">{{ $t('camera.live.settings_title') }}</div>
          <div style="max-width: 600px;">

            <!-- Stream camera mode -->
            <div class="form-group">
              <label class="form-label">{{ $t('camera.live.mode_select_label') }}</label>
              <div v-if="modes.length === 0" class="info-block" style="margin-top: var(--spacing-xs);">
                <span style="color: var(--color-text-secondary);">{{ $t('camera.camera.modes_unavailable') }}</span>
                <span v-if="streamSettings.stream_camera_mode_str">
                  {{ $t('camera.camera.current_mode') }} <strong>{{ streamSettings.stream_camera_mode_str }}</strong>
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
              <label class="form-label">{{ $t('camera.live.resolution_select') }}</label>
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

      // Storage / files limit. storageStats is fetched once and cached; the
      // estimate is recomputed on the frontend as filesLimit changes.
      storageStats: null,
      filesLimit: 400,
      savingLimit: false,

      error: '',
      success: '',
      actionLoading: null
    };
  },

  computed: {
    tabs() {
      return [
        { value: 'info', label: this.$t('camera.camera.info_tab') },
        { value: 'settings', label: this.$t('camera.camera.settings_tab') }
      ];
    },

    cameraModel() {
      if (!this.info) return '—';
      return this.info.model || this.$t('camera.camera.no_camera');
    },

    videoState() {
      return this.info ? this.info.video_state : null;
    },

    videoStateLabel() {
      const labels = {
        record: this.$t('camera.camera.state_record'),
        pause: this.$t('camera.camera.state_pause'),
        stop: this.$t('camera.camera.state_stop')
      };
      return labels[this.videoState] || '—';
    },

    thermalStatusLabel() {
      const labels = {
        normal: this.$t('camera.camera.thermal_normal'),
        downscaled: this.$t('camera.camera.thermal_downscaled'),
        overheated: this.$t('camera.camera.thermal_overheated'),
      };
      return labels[this.info?.thermal_status] || '—';
    },

    avgFileBytes() {
      return this.storageStats?.avg_file_bytes || 0;
    },

    // Largest file count that still keeps the reserve (default 20%) of the disk free.
    maxAllowedFiles() {
      if (!this.storageStats) return null;
      const disk = this.storageStats.disk_total_bytes || 0;
      const reserve = this.storageStats.disk_reserve_fraction ?? 0.2;
      if (!disk || !this.avgFileBytes) return null;
      const usable = disk * (1 - reserve);
      return Math.max(1, Math.floor(usable / this.avgFileBytes));
    },

    estimatedBytes() {
      const n = parseInt(this.filesLimit, 10);
      if (!n || n < 0 || !this.avgFileBytes) return 0;
      return n * this.avgFileBytes;
    },

    isLimitValid() {
      const n = parseInt(this.filesLimit, 10);
      return Number.isInteger(n) && n >= 1;
    },

    limitExceeded() {
      if (this.maxAllowedFiles === null) return false;
      const n = parseInt(this.filesLimit, 10);
      return Number.isInteger(n) && n > this.maxAllowedFiles;
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
          this.error = result.error || this.$t('camera.camera.error_load');
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
          this.error = infoData.error || this.$t('camera.camera.error_load_settings');
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
          this.error = result.error || this.$t('camera.camera.error_start');
          return;
        }
        this.success = this.$t('camera.camera.record_started');
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
          this.error = result.error || this.$t('camera.camera.error_pause');
          return;
        }
        this.success = this.$t('camera.camera.record_paused');
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
          this.error = result.error || this.$t('camera.camera.error_save');
          return;
        }
        this.success = this.$t('camera.camera.settings_saved');
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.saving = false;
      }
    },

    formatBytes(bytes) {
      if (!bytes || bytes <= 0) return '0 B';
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      let value = bytes;
      let i = 0;
      while (value >= 1024 && i < units.length - 1) {
        value /= 1024;
        i++;
      }
      const digits = value >= 100 || i === 0 ? 0 : 1;
      return value.toFixed(digits) + ' ' + units[i];
    },

    async loadStorageStats() {
      try {
        const response = await fetch('/api/camera/storage_stats', { credentials: 'same-origin' });
        const result = await response.json();
        if (!response.ok) return;
        this.storageStats = result;
        this.filesLimit = result.max_files;
      } catch (err) {
        // Non-critical: the counter simply won't render without stats.
      }
    },

    async saveFilesLimit() {
      this.error = '';
      this.success = '';
      if (!this.isLimitValid || this.limitExceeded) return;
      this.savingLimit = true;
      try {
        const response = await fetch('/api/camera/files_limit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ max_files: parseInt(this.filesLimit, 10) })
        });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('camera.camera.error_limit_save');
          return;
        }
        this.success = this.$t('camera.camera.limit_saved');
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.savingLimit = false;
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
          this.error = result.error || this.$t('camera.live.error_save');
          return;
        }
        this.success = this.$t('camera.camera.settings_saved');
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.savingStream = false;
      }
    }
  },

  async mounted() {
    await Promise.all([this.loadInfo(), this.loadSettings(), this.loadStorageStats()]);
  }
};

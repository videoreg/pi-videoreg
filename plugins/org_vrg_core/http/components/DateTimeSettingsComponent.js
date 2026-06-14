// Date & Time settings page (core plugin): view and set system date, time and
// timezone, and toggle automatic time synchronization (NTP).
const DateTimeSettingsComponent = {
  components: { Icon, ToggleSwitch },
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('core.datetime.title') }}</h1>
        <div v-if="loading" class="spinner spinner-sm"></div>
        <button v-else class="btn btn-icon" @click="load" :disabled="loading" :title="$t('http.common.refresh')">↻</button>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="success" class="alert alert-success">{{ success }}</div>
      <div v-if="state && !state.supported" class="alert alert-info">{{ $t('core.datetime.not_supported') }}</div>

      <div v-if="state" class="info-block">
        <div class="section-title">{{ $t('core.datetime.current_title') }}</div>
        <div class="info-rows">
          <div class="info-row">
            <span class="info-label">{{ $t('core.datetime.current_time') }}</span>
            <strong>{{ formatCurrent(state.datetime) }}</strong>
          </div>
          <div class="info-row">
            <span class="info-label">{{ $t('core.datetime.timezone_label') }}</span>
            <strong>{{ state.timezone || '—' }}</strong>
          </div>
          <div class="info-row">
            <span class="info-label">{{ $t('core.datetime.ntp_label') }}</span>
            <span class="status-indicator" style="padding: 3px 8px;">
              <span class="status-dot" :class="{ active: state.ntp }"></span>
              <span>{{ state.ntp ? $t('core.datetime.ntp_on') : $t('core.datetime.ntp_off') }}</span>
            </span>
          </div>
        </div>
      </div>

      <div v-if="state" class="info-block">
        <div class="section-title">{{ $t('core.datetime.ntp_title') }}</div>
        <p style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary);">
          {{ $t('core.datetime.ntp_hint') }}
        </p>
        <toggle-switch
          v-model="ntp"
          :disabled="ntpSaving || !state.supported"
          @update:modelValue="onNtpToggle"
        ></toggle-switch>
      </div>

      <div v-if="state" class="info-block">
        <div class="section-title">{{ $t('core.datetime.set_time_title') }}</div>
        <p style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary);">
          {{ $t('core.datetime.set_time_hint') }}
        </p>
        <div style="max-width: 400px;">
          <div style="margin-bottom: var(--spacing-md);">
            <label style="display: block; margin-bottom: var(--spacing-sm); color: var(--color-text-secondary); font-size: 0.875rem;">
              {{ $t('core.datetime.datetime_label') }}
            </label>
            <input type="datetime-local" v-model="dtInput" class="form-input" step="1" :disabled="timeSaving || !state.supported">
          </div>
          <button class="btn btn-primary" @click="saveTime" :disabled="timeSaving || !dtInput || !state.supported">
            {{ timeSaving ? $t('common.saving') : $t('common.save') }}
          </button>
        </div>
      </div>

      <div v-if="state" class="info-block">
        <div class="section-title">{{ $t('core.datetime.set_timezone_title') }}</div>
        <div style="max-width: 400px;">
          <div style="margin-bottom: var(--spacing-md);">
            <label style="display: block; margin-bottom: var(--spacing-sm); color: var(--color-text-secondary); font-size: 0.875rem;">
              {{ $t('core.datetime.timezone_select_label') }}
            </label>
            <select v-model="tzInput" class="form-input" :disabled="tzSaving || !state.supported">
              <option v-for="tz in state.timezones" :key="tz" :value="tz">{{ tz }}</option>
            </select>
          </div>
          <button class="btn btn-primary" @click="saveTimezone" :disabled="tzSaving || !tzInput || tzInput === state.timezone || !state.supported">
            {{ tzSaving ? $t('common.saving') : $t('common.save') }}
          </button>
        </div>
      </div>
    </div>
  `,

  data() {
    return {
      state: null,
      loading: false,
      error: '',
      success: '',
      ntp: false,
      ntpSaving: false,
      dtInput: '',
      timeSaving: false,
      tzInput: '',
      tzSaving: false,
    };
  },

  methods: {
    formatCurrent(value) {
      if (!value) return '—';
      return value.replace('T', ' ');
    },

    applyState(state) {
      this.state = state;
      this.ntp = !!state.ntp;
      this.dtInput = (state.datetime || '').slice(0, 19);
      this.tzInput = state.timezone || '';
    },

    async load() {
      this.error = '';
      this.loading = true;
      try {
        const response = await fetch('/api/core/datetime', { credentials: 'same-origin' });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('core.datetime.error_load');
          return;
        }
        this.applyState(result);
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    },

    flashSuccess() {
      this.success = this.$t('core.datetime.saved');
      setTimeout(() => { this.success = ''; }, 2000);
    },

    async onNtpToggle(value) {
      this.error = '';
      this.success = '';
      this.ntpSaving = true;
      try {
        const response = await fetch('/api/core/ntp', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: value }),
        });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('core.datetime.error_save');
          this.ntp = !value;
          return;
        }
        this.applyState(result);
        this.flashSuccess();
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
        this.ntp = !value;
      } finally {
        this.ntpSaving = false;
      }
    },

    async saveTime() {
      this.error = '';
      this.success = '';
      this.timeSaving = true;
      try {
        const response = await fetch('/api/core/datetime', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ datetime: this.dtInput }),
        });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('core.datetime.error_save');
          return;
        }
        this.applyState(result);
        this.flashSuccess();
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.timeSaving = false;
      }
    },

    async saveTimezone() {
      this.error = '';
      this.success = '';
      this.tzSaving = true;
      try {
        const response = await fetch('/api/core/datetime', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ timezone: this.tzInput }),
        });
        const result = await response.json();
        if (!response.ok) {
          this.error = result.error || this.$t('core.datetime.error_save');
          return;
        }
        this.applyState(result);
        this.flashSuccess();
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.tzSaving = false;
      }
    },
  },

  async mounted() {
    await this.load();
  },
};

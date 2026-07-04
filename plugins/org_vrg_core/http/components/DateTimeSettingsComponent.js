// Date & Time settings page (core plugin): view and set system date, time and
// timezone, and toggle automatic time synchronization (NTP).
//
// Also reused during first-run onboarding (after a forced password change): with
// `onboarding` set the back button and NTP toggle are hidden and a
// "Continue with these settings" button is shown, which emits `done`.
const DateTimeSettingsComponent = {
  components: { Icon, ToggleSwitch },
  props: {
    onboarding: { type: Boolean, default: false },
  },
  emits: ['navigate', 'done'],

  template: `
    <div :class="{ 'onboarding-page': onboarding }">
      <div v-if="onboarding" class="onboarding-header">
        <h1>Videoreg</h1>
        <p>{{ $t('core.datetime.onboarding_hint') }}</p>
      </div>
      <div v-else class="page-header">
        <button class="btn-back" @click="$emit('navigate', 'settings')" :title="$t('common.back')"><icon name="chevron-left" :size="28"></icon></button>
        <h1 class="page-title">{{ $t('core.datetime.title') }}</h1>
        <div v-if="loading" class="spinner spinner-sm"></div>
        <button v-else class="btn btn-icon" @click="load" :disabled="loading" :title="$t('http.common.refresh')">↻</button>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="success" class="alert alert-success">{{ success }}</div>
      <div v-if="state && !state.supported" class="alert alert-info">{{ $t('core.datetime.not_supported') }}</div>

      <div v-if="state" class="info-block">
        <div class="section-title">{{ $t('core.datetime.set_time_title') }}</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--spacing-lg); max-width: 640px;">
          <div>
            <div style="margin-bottom: var(--spacing-md);">
              <label style="display: block; margin-bottom: var(--spacing-sm); color: var(--color-text-secondary); font-size: 0.875rem;">
                {{ $t('core.datetime.datetime_label') }}
              </label>
              <input type="datetime-local" v-model="dtInput" class="form-input" step="1" :disabled="timeSaving || !state.supported">
            </div>
            <div style="margin-bottom: var(--spacing-md);">
              <label style="display: block; margin-bottom: var(--spacing-sm); color: var(--color-text-secondary); font-size: 0.875rem;">
                {{ $t('core.datetime.timezone_select_label') }}
              </label>
              <select v-model="tzInput" class="form-input" :disabled="timeSaving || !state.supported">
                <option v-for="tz in state.timezones" :key="tz" :value="tz">{{ tz }}</option>
              </select>
            </div>
            <button class="btn btn-primary" @click="saveTime" :disabled="timeSaving || !dtInput || !tzInput || !state.supported">
              {{ timeSaving ? $t('common.saving') : $t('core.datetime.set_this_time') }}
            </button>
          </div>
          <div>
            <div style="margin-bottom: var(--spacing-md);">
              <label style="display: block; margin-bottom: var(--spacing-sm); color: var(--color-text-secondary); font-size: 0.875rem;">
                {{ $t('core.datetime.browser_time_label') }}
              </label>
              <input type="text" :value="formatCurrent(browserTime)" class="form-input" readonly>
            </div>
            <div style="margin-bottom: var(--spacing-md);">
              <label style="display: block; margin-bottom: var(--spacing-sm); color: var(--color-text-secondary); font-size: 0.875rem;">
                {{ $t('core.datetime.timezone_select_label') }}
              </label>
              <input type="text" :value="browserTz" class="form-input" readonly>
            </div>
            <button class="btn btn-primary" @click="saveBrowserTime" :disabled="timeSaving || !state.supported">
              {{ timeSaving ? $t('common.saving') : $t('core.datetime.set_from_browser') }}
            </button>
          </div>
        </div>
        <p style="margin-top: var(--spacing-md); color: var(--color-text-secondary);">
          {{ $t('core.datetime.set_time_hint') }}
        </p>
        <button v-if="onboarding" class="btn btn-primary btn-block" style="margin-top: var(--spacing-md);" @click="$emit('done')">
          {{ $t('core.datetime.continue') }}
        </button>
      </div>

      <div v-if="state && !onboarding" class="info-block">
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
      browserTime: '',
      browserTz: '',
      browserTimer: null,
      timeSaving: false,
      tzInput: '',
    };
  },

  methods: {
    formatCurrent(value) {
      if (!value) return '—';
      return value.replace('T', ' ');
    },

    // Current browser wall-clock time as a `YYYY-MM-DDTHH:MM:SS` string.
    localDatetime() {
      const d = new Date();
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
        `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    },

    // Browser's IANA timezone name (e.g. "Europe/Moscow").
    localTimezone() {
      try {
        return Intl.DateTimeFormat().resolvedOptions().timeZone || '';
      } catch (err) {
        return '';
      }
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

    // Apply date/time and timezone together. `payload` omits empty fields.
    async setDatetime(payload) {
      this.error = '';
      this.success = '';
      this.timeSaving = true;
      try {
        const response = await fetch('/api/core/datetime', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
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

    async saveTime() {
      await this.setDatetime({ datetime: this.dtInput, timezone: this.tzInput });
    },

    async saveBrowserTime() {
      const payload = { datetime: this.localDatetime() };
      if (this.browserTz) payload.timezone = this.browserTz;
      await this.setDatetime(payload);
    },
  },

  async mounted() {
    this.browserTz = this.localTimezone();
    this.browserTime = this.localDatetime();
    this.browserTimer = setInterval(() => { this.browserTime = this.localDatetime(); }, 1000);
    await this.load();
  },

  beforeUnmount() {
    if (this.browserTimer) clearInterval(this.browserTimer);
  },
};

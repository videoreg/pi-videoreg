const GpsTracksComponent = {
  components: { TabSwitch, Icon },
  template: `
    <div>
      <div class="page-header">
        <h1 class="page-title">{{ $t('http.gps_tracks.title') }}</h1>
        <div style="display: flex; gap: var(--spacing-sm);">
          <div v-if="loading" class="spinner spinner-sm"></div>
          <button v-else class="btn btn-icon" @click="load" :title="$t('http.common.refresh')">↻</button>
        </div>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div v-if="tracks.length === 0 && !loading" class="alert alert-info">
        {{ $t('http.gps_tracks.no_tracks') }}
      </div>

      <template v-if="tracks.length > 0">
        <tab-switch
          v-model="activeDate"
          :tabs="dateTabs"
          style="margin-bottom: var(--spacing-lg);"
        />

        <div
          v-for="track in activeTracks"
          :key="track.filename"
          class="media-feed-item"
          style="display: block;"
        >
          <div class="media-feed-info" style="padding: var(--spacing-md);">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-sm);">
              <div style="display: flex; align-items: center; gap: var(--spacing-sm);">
                <icon name="gps_tracks" :size="20"></icon>
                <span style="font-weight: 600; color: var(--color-text-primary);">{{ track.time }}</span>
              </div>
              <div style="display: flex; align-items: center; gap: var(--spacing-sm);">
                <a
                  :href="'/gps/' + track.filename"
                  download
                  class="btn btn-ghost"
                  style="text-decoration: none;"
                >{{ $t('http.gps_tracks.download') }}</a>
                <button
                  class="btn-icon"
                  style="color: var(--color-error); opacity: 0.7; padding: 2px;"
                  :title="$t('common.delete')"
                  @click="deleteTrack(track)"
                ><icon name="delete" :size="20"></icon></button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  `,

  data() {
    return {
      tracks: [],
      activeDate: null,
      error: '',
      loading: false
    };
  },

  computed: {
    dates() {
      const s = new Set();
      for (const track of this.tracks) {
        s.add(track.date);
      }
      return [...s].sort().reverse();
    },

    dateTabs() {
      return this.dates.map(d => ({ value: d, label: this.formatDateTab(d) }));
    },

    activeTracks() {
      if (!this.activeDate) return [];
      return this.tracks.filter(t => t.date === this.activeDate);
    }
  },

  methods: {
    async load() {
      this.error = '';
      this.loading = true;
      try {
        const response = await fetch('/api/gps/tracks', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('http.gps_tracks.error_load');
          return;
        }
        this.tracks = data.tracks || [];
        this.activeDate = this.dates[0] || null;
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    },

    formatDateTab(dateStr) {
      try {
        const d = new Date(dateStr + 'T00:00:00');
        return d.toLocaleDateString(VrgI18n.locale, { day: 'numeric', month: 'short', weekday: 'short' });
      } catch (e) {
        return dateStr;
      }
    },

    async deleteTrack(track) {
      if (!confirm(this.$t('http.gps_tracks.confirm_delete', { time: track.time }))) return;
      try {
        const response = await fetch(`/api/gps/tracks/${encodeURIComponent(track.filename)}`, {
          method: 'DELETE',
          credentials: 'same-origin'
        });
        if (!response.ok) {
          const data = await response.json();
          this.error = data.error || this.$t('http.gps_tracks.error_delete');
          return;
        }
        this.tracks = this.tracks.filter(t => t.filename !== track.filename);
        if (this.activeTracks.length === 0) {
          this.activeDate = this.dates[0] || null;
        }
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      }
    }
  },

  async mounted() {
    await this.load();
  }
};

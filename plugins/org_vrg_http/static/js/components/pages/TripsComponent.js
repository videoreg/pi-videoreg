const TripsComponent = {
  components: { Icon, TripsMediaItem },

  template: `
    <div>
      <div class="page-header">
        <h1 class="page-title">{{ $t('http.trips.title') }}</h1>
        <div style="display: flex; gap: var(--spacing-sm);">
          <div v-if="loading" class="spinner spinner-sm"></div>
          <button v-else class="btn btn-icon" @click="load" :title="$t('http.common.refresh')">↻</button>
        </div>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div v-if="!loading && blocks.length === 0 && !error" class="alert alert-info">
        {{ $t('http.trips.no_data') }}
      </div>

      <div v-for="(block, idx) in blocks" :key="block.kind + block.start" class="trips-block" :class="'trips-block--' + block.kind">
        <div class="trips-block-header">
          <span class="trips-block-label">{{ blockLabel(block) }}:</span>
          <span class="trips-block-duration">{{ blockDuration(block) }}</span>
          <span class="trips-block-time">{{ blockTimeStr(block) }}</span>
          <template v-if="block.tracks && block.tracks.length > 0">
            <a
              v-for="(track, tIdx) in block.tracks"
              :key="tIdx"
              :href="'/gps/' + stripExt(track)"
              download
              class="btn btn-ghost btn-sm trips-track-btn"
            ><icon name="gps_tracks" :size="16"></icon> {{ $t('http.trips.track_btn') }}</a>
          </template>
        </div>

        <template v-if="block.media && block.media.length > 0">
          <button class="trips-block-expand" @click="toggleExpand(idx)">
            {{ expanded[idx] ? $t('http.trips.collapse') : $t('http.trips.expand', { count: block.media.length }) }}
          </button>

          <div v-if="expanded[idx]">
            <div class="trips-block-media media-grid">
              <trips-media-item
                v-for="item in mediaPage(idx, block.media)"
                :key="item.filename"
                :item="item"
              ></trips-media-item>
            </div>
            <div v-if="block.media.length > PAGE_SIZE" class="trips-block-pagination">
              <button
                v-for="p in Math.ceil(block.media.length / PAGE_SIZE)"
                :key="p"
                class="trips-pagination-btn"
                :class="{ 'trips-pagination-btn--active': (mediaPages[idx] || 0) === p - 1 }"
                @click="setPage(idx, p - 1)"
              >{{ p }}</button>
            </div>
          </div>
        </template>
      </div>
    </div>
  `,

  data() {
    return {
      blocks: [],
      expanded: {},
      mediaPages: {},
      PAGE_SIZE: 10,
      error: '',
      loading: false
    };
  },

  methods: {
    async load() {
      this.error = '';
      this.loading = true;
      try {
        const response = await fetch('/api/core/journal', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('http.trips.error_load');
          return;
        }
        const events = this.parseLines(data.lines || []);
        this.blocks = this.buildBlocks(events);
        this.expanded = {};
        this.mediaPages = {};
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    },

    parseLines(lines) {
      const events = [];
      for (const line of lines) {
        if (!line) continue;
        const idx1 = line.indexOf(',');
        if (idx1 === -1) continue;
        const idx2 = line.indexOf(',', idx1 + 1);
        if (idx2 === -1) continue;
        const idx3 = line.indexOf(',', idx2 + 1);
        if (idx3 === -1) continue;
        const date = line.slice(0, idx1);
        const plugin = line.slice(idx1 + 1, idx2);
        const type = line.slice(idx2 + 1, idx3);
        const dataStr = line.slice(idx3 + 1);
        let eventData = null;
        try {
          eventData = JSON.parse(dataStr);
        } catch (e) {
          // ignore parse errors
        }
        events.push({ date, plugin, type, data: eventData });
      }
      events.sort((a, b) => a.date.localeCompare(b.date));
      return events;
    },

    buildBlocks(events) {
      const relevantTypes = new Set(['charging_on', 'charging_off', 'stop', 'jpeg', 'h264', 'track_created']);
      const blocks = [];
      let current = null;

      for (const event of events) {
        if (!relevantTypes.has(event.type)) continue;

        if (event.type === 'charging_on') {
          if (current && current.kind === 'parking') {
            current.end = event.date;
            current = null;
          }
          if (!current || current.kind !== 'trip') {
            current = { kind: 'trip', start: event.date, end: null, media: [], tracks: [] };
            blocks.push(current);
          }

        } else if (event.type === 'charging_off') {
          if (current && current.kind === 'trip') {
            current.end = event.date;
            current = null;
          }
          if (!current || current.kind !== 'parking') {
            current = { kind: 'parking', start: event.date, end: null, media: [], tracks: [] };
            blocks.push(current);
          }

        } else if (event.type === 'stop') {
          if (current && current.kind === 'trip') {
            current.end = event.date;
            current = null;
          }

        } else if (event.type === 'jpeg' || event.type === 'h264') {
          if (current && event.data && event.data.filename) {
            const mediaType = event.type === 'jpeg' ? 'photo' : 'video';
            const base = this.stripExt(event.data.filename);
            const existing = current.media.find(m => this.stripExt(m.filename) === base);
            if (existing) {
              if (mediaType === 'video') {
                // jpeg пришёл раньше h264 — сохраняем его как скриншот
                existing.screenshot = existing.filename;
                existing.type = 'video';
                existing.filename = event.data.filename;
              } else {
                // jpeg пришёл после h264 — это скриншот к видео
                existing.screenshot = event.data.filename;
              }
            } else {
              current.media.push({ type: mediaType, filename: event.data.filename, date: event.date });
            }
          }

        } else if (event.type === 'track_created') {
          if (current && event.data && event.data.filename) {
            current.tracks.push(event.data.filename);
          }
        }
      }

      // Handle unclosed block
      if (current) {
        if (current.kind === 'trip') {
          current.kind = 'in_trip';
        } else if (current.kind === 'parking') {
          current.kind = 'parked';
        }
      }

      for (const b of blocks) b.media.reverse();
      return blocks.reverse();
    },

    blockLabel(block) {
      const labels = {
        trip: this.$t('http.trips.kind_trip'),
        parking: this.$t('http.trips.kind_parking'),
        in_trip: this.$t('http.trips.kind_in_trip'),
        parked: this.$t('http.trips.kind_parked')
      };
      return labels[block.kind] || block.kind;
    },

    blockDuration(block) {
      const start = new Date(block.start);
      const end = block.end ? new Date(block.end) : new Date();
      const diffMs = end - start;
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return this.$t('http.trips.less_than_min');
      if (diffMin < 60) return this.$t('http.trips.duration_min', { m: diffMin });
      const h = Math.floor(diffMin / 60);
      const m = diffMin % 60;
      return m > 0 ? this.$t('http.trips.duration_h_m', { h, m }) : this.$t('http.trips.duration_h', { h });
    },

    blockTimeStr(block) {
      const dateStr = this.formatDate(block.start);
      const startStr = this.formatTime(block.start);
      if (!block.end) {
        return dateStr + ' ' + this.$t('http.trips.time_from', { time: startStr });
      }
      return dateStr + ' ' + startStr + ' — ' + this.formatTime(block.end);
    },

    formatDate(dateStr) {
      if (!dateStr) return '—';
      try {
        const d = new Date(dateStr);
        return d.toLocaleDateString(VrgI18n.locale, { day: 'numeric', month: 'long' });
      } catch (e) {
        return '';
      }
    },

    formatTime(dateStr) {
      if (!dateStr) return '—';
      try {
        const d = new Date(dateStr);
        return d.toLocaleTimeString(VrgI18n.locale, { hour: '2-digit', minute: '2-digit' });
      } catch (e) {
        return dateStr;
      }
    },

    toggleExpand(idx) {
      this.expanded = { ...this.expanded, [idx]: !this.expanded[idx] };
      if (!this.expanded[idx]) {
        const p = { ...this.mediaPages };
        delete p[idx];
        this.mediaPages = p;
      }
    },

    mediaPage(idx, media) {
      const page = this.mediaPages[idx] || 0;
      return media.slice(page * this.PAGE_SIZE, (page + 1) * this.PAGE_SIZE);
    },

    setPage(idx, page) {
      this.mediaPages = { ...this.mediaPages, [idx]: page };
    },

    stripExt(filename) {
      const lastDot = filename.lastIndexOf('.');
      return lastDot > 0 ? filename.slice(0, lastDot) : filename;
    }
  },

  async mounted() {
    await this.load();
  }
};

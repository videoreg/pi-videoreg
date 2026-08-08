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
            <ul v-if="block.eventLog && block.eventLog.length > 0" class="trips-thermal-log">
              <li v-for="(entry, eIdx) in collapsedLog(block.eventLog)" :key="eIdx">
                <span class="trips-thermal-log-time">{{ formatTime(entry.date) }}</span> {{ entry.label }}<span v-if="entry.count > 1" class="trips-thermal-log-count"> ×{{ entry.count }}</span>
              </li>
            </ul>
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
        // The journal remembers every track ever announced, but the GPS folder is the
        // truth about what can still be downloaded — old tracks are rotated away by the
        // media cleanup, and fix-less ones are deleted outright. Fetch both.
        const [response, tracksResponse] = await Promise.all([
          fetch('/api/core/journal', { credentials: 'same-origin' }),
          fetch('/api/gps/tracks', { credentials: 'same-origin' }).catch(() => null)
        ]);
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('http.trips.error_load');
          return;
        }
        // null means the list is unavailable — then show every track rather than none.
        let existingTracks = null;
        if (tracksResponse && tracksResponse.ok) {
          const tracksData = await tracksResponse.json();
          existingTracks = new Set((tracksData.tracks || []).map(t => this.stripExt(t.filename)));
        }
        const events = this.parseLines(data.lines || []);
        this.blocks = this.buildBlocks(events, existingTracks);
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

    buildBlocks(events, existingTracks = null) {
      const THERMAL_TYPES = new Set(['thermal_throttle_on', 'thermal_throttle_off', 'thermal_overheated']);
      const BEACON_TYPES = new Set(['beacon_found', 'beacon_lost', 'beacon_enabled', 'beacon_disabled']);
      // Events that clear a "beacon absent" state: the beacon returned, or the
      // feature was toggled (enabling/disabling stops it from gating trips).
      const BEACON_CLEARS = new Set(['beacon_found', 'beacon_enabled', 'beacon_disabled']);

      // A trip is when the vehicle is running. With the BLE-beacon feature the
      // engine may keep external power flowing even while parked, so power alone
      // no longer marks a trip. We segment on the same "effective" state the
      // shutdown engine uses: power present AND the beacon is not confirmed
      // absent. When the feature is off there are no beacon events, so this
      // degrades to the classic power-only (charging_on/off) segmentation.

      // --- Pass 1: classify each beacon_lost as transient or real. A loss is
      // real only if a beacon_lost shutdown follows before the beacon returns;
      // a flaky beacon that blinks and reappears must not split a trip. ---
      const realLoss = new Set(); // event indices of confirmed (real) losses
      for (let i = 0; i < events.length; i++) {
        if (events[i].type !== 'beacon_lost') continue;
        for (let j = i + 1; j < events.length; j++) {
          const e = events[j];
          if (BEACON_CLEARS.has(e.type)) break; // recovered or feature toggled → transient
          if (e.type === 'shutdown' && e.data && e.data.reason === 'beacon_lost') {
            realLoss.add(i); // grace expired → the loss was real
            break;
          }
        }
      }

      // --- Pass 1b: mark sessions that were beacon-absent from the very start. A
      // beacon that is already gone when the scanner starts produces no beacon_lost
      // event at all — the presence loop only reports present<->absent transitions and
      // a session begins as "absent" — so a parking wake-up leaves nothing behind but
      // charging_on (external power is still there) and a beacon-lost shutdown. A
      // session (delimited by core's `start` events) that ends in a beacon-lost
      // shutdown without ever seeing the beacon therefore *was* a parking wake-up, and
      // saying so explicitly is what keeps an RTC wake-up storm from looking like a
      // trip once the beacon_lost that opened the parking scrolls out of the journal
      // window (the page only loads the last two days). ---
      const absentSessionStart = new Set(); // event index that opens such a session
      let sessionStart = 0;      // index of the current session's `start` event
      let sawBeacon = false;     // beacon confirmed present during this session
      let endedBeaconLost = false;
      for (let i = 0; i <= events.length; i++) {
        const isBoundary = i === events.length || events[i].type === 'start';
        if (isBoundary) {
          if (endedBeaconLost && !sawBeacon) absentSessionStart.add(sessionStart);
          sessionStart = i;
          sawBeacon = false;
          endedBeaconLost = false;
          continue;
        }
        const e = events[i];
        if (BEACON_CLEARS.has(e.type)) sawBeacon = true;
        else if (e.type === 'shutdown') {
          endedBeaconLost = !!(e.data && e.data.reason === 'beacon_lost');
        }
      }

      // --- Pass 2: build ordered segments from the effective state. Only power
      // and (real) beacon transitions move the boundary, so the grace-window
      // recordings between a real loss and its shutdown land in the parking,
      // and repeated RTC wake-ups during a parking (each emits charging_on) do
      // not spawn new trips while the beacon stays absent. ---
      const segments = []; // { kind: 'trip'|'parking', start, end }
      let charging = null;      // null until the first power event is seen
      let beaconAbsent = false; // true after a real loss, until the beacon returns
      let cur = null;

      const apply = (date) => {
        if (charging === null) return; // effective state not yet known
        const kind = (charging === true && !beaconAbsent) ? 'trip' : 'parking';
        if (cur && cur.kind === kind) return;
        if (cur) cur.end = date;
        cur = { kind, start: date, end: null };
        segments.push(cur);
      };

      for (let i = 0; i < events.length; i++) {
        const e = events[i];
        // A beacon-absent session (pass 1b) marks the beacon gone before its own
        // charging_on is seen, so the wake-up never opens a trip.
        if (absentSessionStart.has(i)) { beaconAbsent = true; apply(e.date); }
        if (e.type === 'charging_on') { charging = true; apply(e.date); }
        else if (e.type === 'charging_off') { charging = false; apply(e.date); }
        else if (BEACON_CLEARS.has(e.type)) { beaconAbsent = false; apply(e.date); }
        else if (e.type === 'beacon_lost' && realLoss.has(i)) { beaconAbsent = true; apply(e.date); }
      }

      if (segments.length === 0) return [];

      // --- Pass 3: bucket media / tracks / eventLog into the segment covering
      // each event's timestamp. ---
      const blocks = segments.map(s => ({
        kind: s.kind, start: s.start, end: s.end, media: [], tracks: [], eventLog: []
      }));
      let segIdx = -1;

      for (const event of events) {
        // Advance to the segment whose [start, end) contains this event.
        while (segIdx + 1 < segments.length && event.date >= segments[segIdx + 1].start) segIdx++;
        if (segIdx < 0) continue; // event predates the first segment
        const block = blocks[segIdx];

        if (event.type === 'jpeg' || event.type === 'h264') {
          if (event.data && event.data.filename) {
            const mediaType = event.type === 'jpeg' ? 'photo' : 'video';
            const base = this.stripExt(event.data.filename);
            const existing = block.media.find(m => this.stripExt(m.filename) === base);
            if (existing) {
              if (mediaType === 'video') {
                // jpeg came before h264 — keep it as the screenshot
                existing.screenshot = existing.filename;
                existing.type = 'video';
                existing.filename = event.data.filename;
              } else {
                // jpeg came after h264 — it is the video's screenshot
                existing.screenshot = event.data.filename;
              }
            } else {
              block.media.push({ type: mediaType, filename: event.data.filename, date: event.date });
            }
          }

        } else if (event.type === 'track_created') {
          const trackFile = event.data && event.data.filename;
          if (trackFile && (!existingTracks || existingTracks.has(this.stripExt(trackFile)))) {
            block.tracks.push(trackFile);
          }

        } else if (THERMAL_TYPES.has(event.type)) {
          block.eventLog.push({ category: 'thermal', type: event.type, date: event.date, data: event.data });

        } else if (BEACON_TYPES.has(event.type)) {
          block.eventLog.push({ category: 'beacon', type: event.type, date: event.date });

        } else if (event.type === 'shutdown') {
          block.eventLog.push({ category: 'shutdown', reason: event.data && event.data.reason, date: event.date });
        }
      }

      // Keep each block's event log in strict chronological order (single timeline).
      for (const b of blocks) b.eventLog.sort((a, c) => a.date.localeCompare(c.date));

      // The last segment is still open — mark it as the ongoing trip/parking.
      const last = blocks[blocks.length - 1];
      if (last.kind === 'trip') last.kind = 'in_trip';
      else if (last.kind === 'parking') last.kind = 'parked';

      for (const b of blocks) b.media.reverse();
      return blocks.reverse();
    },

    // Collapse consecutive identical entries (e.g. an RTC wake-up storm that
    // shuts down on a lost beacon dozens of times) into one line with a count,
    // keeping the timestamp of the first occurrence.
    collapsedLog(eventLog) {
      const out = [];
      for (const entry of eventLog) {
        const label = this.eventLabel(entry);
        const prev = out[out.length - 1];
        if (prev && prev.label === label) {
          prev.count++;
        } else {
          out.push({ label, date: entry.date, count: 1 });
        }
      }
      return out;
    },

    eventLabel(entry) {
      if (entry.category === 'beacon') {
        const labels = {
          beacon_found: this.$t('http.trips.beacon_found'),
          beacon_lost: this.$t('http.trips.beacon_lost'),
          beacon_enabled: this.$t('http.trips.beacon_enabled'),
          beacon_disabled: this.$t('http.trips.beacon_disabled')
        };
        return labels[entry.type] || entry.type;
      }
      if (entry.category === 'shutdown') {
        const labels = {
          forced: this.$t('http.trips.shutdown_forced'),
          power_loss: this.$t('http.trips.shutdown_power_loss'),
          beacon_lost: this.$t('http.trips.shutdown_beacon_lost')
        };
        return labels[entry.reason] || this.$t('http.trips.shutdown_unknown');
      }
      // thermal (or any other): show the raw type plus any data payload
      return entry.type + (entry.data ? ' ' + JSON.stringify(entry.data) : '');
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

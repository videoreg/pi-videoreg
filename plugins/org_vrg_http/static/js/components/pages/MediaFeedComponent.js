const MediaFeedComponent = {
  components: { TabSwitch, TripsMediaItem },

  template: `
    <div>
      <div class="page-header">
        <h1 class="page-title">{{ $t('http.media_feed.title') }}</h1>
        <div style="display: flex; gap: var(--spacing-sm);">
          <div v-if="loading" class="spinner spinner-sm"></div>
          <button v-else class="btn btn-icon" @click="loadAll" :title="$t('http.common.refresh')">↻</button>
        </div>
      </div>

<div v-if="error" class="alert alert-error">{{ error }}</div>

      <div v-if="allItems.length === 0 && !loading" class="alert alert-info">
        {{ $t('http.media_feed.no_media') }}
      </div>

      <template v-if="allItems.length > 0">
        <tab-switch
          v-model="activeDate"
          :tabs="dateTabs"
          style="margin-bottom: var(--spacing-lg);"
          @update:modelValue="onDateChange"
        />

        <div v-for="group in itemsByInterval" :key="group.key" class="media-feed-group">
          <div class="media-feed-group-header">{{ group.label }}</div>
          <div class="media-feed-grid">
            <trips-media-item
              v-for="item in collapsedItems(group)"
              :key="item.name"
              :item="toTripsItem(item)"
              :initial-video-ready="item.ready"
              :fave="false"
            ></trips-media-item>
            <button
              v-if="needsMore(group)"
              class="media-feed-more-tile"
              @click="expandGroup(group.key)"
            >+{{ moreCount(group) }}</button>
          </div>
        </div>
      </template>
    </div>
  `,

  data() {
    return {
      allItems: [],
      activeDate: null,
      expandedGroups: {},
      error: '',
      loading: false
    };
  },

  computed: {
    dates() {
      const s = new Set();
      for (const item of this.allItems) {
        s.add(item.datetime.slice(0, 10));
      }
      return [...s].sort().reverse();
    },

    dateTabs() {
      return this.dates.map(d => ({ value: d, label: this.formatDateTab(d) }));
    },

    items() {
      if (!this.activeDate) return [];
      return this.allItems.filter(i => i.datetime.slice(0, 10) === this.activeDate);
    },

    itemsByInterval() {
      const groups = {};
      for (const item of this.items) {
        const d = new Date(item.datetime);
        const minute15 = Math.floor(d.getMinutes() / 15) * 15;
        const h = String(d.getHours()).padStart(2, '0');
        const m = String(minute15).padStart(2, '0');
        const key = item.datetime.slice(0, 11) + h + ':' + m;
        if (!groups[key]) groups[key] = [];
        groups[key].push(item);
      }
      return Object.entries(groups)
        .sort((a, b) => b[0].localeCompare(a[0]))
        .map(([key, items]) => ({ key, label: this.intervalLabel(key), items }));
    }
  },

  methods: {
    intervalLabel(key) {
      const timePart = key.slice(11); // "HH:MM"
      const [h, m] = timePart.split(':').map(Number);
      const endH = (m + 15 >= 60) ? h + 1 : h;
      const endM = (m + 15) % 60;
      return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')} – ${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`;
    },

    collapsedItems(group) {
      if (this.expandedGroups[group.key]) {
        return group.items;
      }
      return group.items.slice(0, 1);
    },

    needsMore(group) {
      return !this.expandedGroups[group.key] && group.items.length > 1;
    },

    moreCount(group) {
      return group.items.length - 1;
    },

    expandGroup(key) {
      this.expandedGroups = { ...this.expandedGroups, [key]: true };
    },

    toTripsItem(item) {
      return {
        type: item.type,
        filename: item.name + (item.type === 'photo' ? '.jpg' : '.h264'),
        date: item.datetime,
        screenshot: (item.type === 'video' && item.preview) ? item.preview + '.jpg' : undefined,
        fave: false,
      };
    },

    async loadAll() {
      this.error = '';
      this.loading = true;
      this.expandedGroups = {};
      try {
        const response = await fetch('/api/camera/list_media', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('http.media_feed.error_load');
          return;
        }
        this.allItems = data.items;
        const s = new Set();
        for (const item of this.allItems) {
          s.add(item.datetime.slice(0, 10));
        }
        const sorted = [...s].sort().reverse();
        this.activeDate = sorted[0] || null;
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    },

    onDateChange(date) {
      this.activeDate = date;
      this.expandedGroups = {};
    },

    formatDateTab(dateStr) {
      try {
        const d = new Date(dateStr + 'T00:00:00');
        return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', weekday: 'short' });
      } catch (e) {
        return dateStr;
      }
    },

  },

  async mounted() {
    await this.loadAll();
  }
};

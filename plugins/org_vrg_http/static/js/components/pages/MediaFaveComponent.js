const MediaFaveComponent = {
  components: { TripsMediaItem },

  template: `
    <div>
      <div class="page-header">
        <h1 class="page-title">{{ $t('http.media_fave.title') }}</h1>
        <div style="display: flex; gap: var(--spacing-sm);">
          <div v-if="loading" class="spinner spinner-sm"></div>
          <button v-else class="btn btn-icon" @click="load" :title="$t('http.common.refresh')">↻</button>
        </div>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div v-if="allItems.length === 0 && !loading" class="alert alert-info">
        {{ $t('http.media_fave.no_fave') }}
      </div>

      <template v-if="allItems.length > 0">
        <div class="media-grid">
          <trips-media-item
            v-for="item in currentPageItems"
            :key="item.name"
            :item="toTripsItem(item)"
            :initial-video-ready="item.ready"
            :fave="true"
            @fave-changed="onFaveChanged(item, $event)"
          ></trips-media-item>
        </div>
        <div v-if="allItems.length > PAGE_SIZE" class="trips-block-pagination">
          <button
            v-for="p in pageCount"
            :key="p"
            class="trips-pagination-btn"
            :class="{ 'trips-pagination-btn--active': currentPage === p - 1 }"
            @click="currentPage = p - 1"
          >{{ p }}</button>
        </div>
      </template>
    </div>
  `,

  data() {
    return {
      allItems: [],
      currentPage: 0,
      PAGE_SIZE: 10,
      error: '',
      loading: false
    };
  },

  computed: {
    pageCount() {
      return Math.ceil(this.allItems.length / this.PAGE_SIZE);
    },
    currentPageItems() {
      const start = this.currentPage * this.PAGE_SIZE;
      return this.allItems.slice(start, start + this.PAGE_SIZE);
    }
  },

  methods: {
    toTripsItem(item) {
      return {
        type: item.type,
        filename: item.name + (item.type === 'photo' ? '.jpg' : '.h264'),
        date: item.datetime,
        screenshot: (item.type === 'video' && item.preview) ? item.preview + '.jpg' : undefined,
        fave: true,
      };
    },

    onFaveChanged(item, { faved }) {
      if (!faved) {
        this.allItems = this.allItems.filter(i => i.name !== item.name);
        // Если текущая страница стала пустой — перейти на предыдущую
        if (this.currentPage >= this.pageCount && this.currentPage > 0) {
          this.currentPage--;
        }
      }
    },

    async load() {
      this.error = '';
      this.loading = true;
      this.currentPage = 0;
      try {
        const response = await fetch('/api/camera/fave_list', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || this.$t('http.media_fave.error_load');
          return;
        }
        this.allItems = data.items;
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    }
  },

  async mounted() {
    await this.load();
  }
};

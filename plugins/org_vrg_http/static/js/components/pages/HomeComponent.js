// Home page — a thin host for manifest-driven dashboard blocks.
//
// Blocks are declared decoratively in each plugin's manifest.yaml under
// `http.dashboard` (component + optional api method + order). The backend
// (/api/dashboard/status) resolves the data and returns the ordered blocks;
// this host merely renders each block's Vue component. Interactive tiles can
// inject the provided `dashboard` API to push ephemeral blocks at runtime
// (e.g. a freshly captured photo).
const HomeComponent = {
  emits: ['navigate'],

  template: `
    <div>
      <div class="page-header">
        <h1 class="page-title">{{ $t('http.home.title') }}</h1>
        <div style="display: flex; gap: var(--spacing-sm);">
          <div v-if="loading" class="spinner spinner-sm"></div>
          <button v-else class="btn btn-icon" @click="load" :title="$t('http.common.refresh')">↻</button>
        </div>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div class="dashboard-tiles">
        <component
          v-for="block in orderedBlocks"
          :is="blockComponent(block.component)"
          :key="block.key"
          :data="block.data"
          :loading="loading"
          @navigate="$emit('navigate', $event)"
        ></component>
      </div>
    </div>
  `,

  data() {
    return {
      // Static block structure ({ key, component, order }) from the manifests,
      // injected by the server so tiles render (as shimmers) before data loads.
      manifestBlocks: (window.__vrgDashboard || []).slice(),
      // Per-block data map { key: data } fetched from /api/dashboard/status.
      dataByKey: {},
      runtimeBlocks: [],
      error: '',
      loading: true,
      _seq: 0,
    };
  },

  provide() {
    return {
      // Runtime block API for interactive tiles. `addBlock` expects a block
      // descriptor `{ key, component, order, data }`, where `component` may be a
      // registered name string or a component object (passed directly since it
      // is bundled). Object components are marked raw so Vue does not make the
      // definition reactive. Newer blocks sort before older ones sharing the
      // same order (see orderedBlocks).
      dashboard: {
        addBlock: (block) => {
          const component = block.component && typeof block.component === 'object'
            ? Vue.markRaw(block.component)
            : block.component;
          this.runtimeBlocks.unshift({ ...block, component, _seq: this._seq++ });
        },
        removeBlock: (key) => {
          this.runtimeBlocks = this.runtimeBlocks.filter((b) => b.key !== key);
        },
      },
    };
  },

  computed: {
    orderedBlocks() {
      const manifest = this.manifestBlocks.map((b) => ({
        key: b.key,
        component: b.component,
        order: b.order,
        data: this.dataByKey[b.key] ?? null,
        _seq: -1,
      }));
      return manifest
        .concat(this.runtimeBlocks)
        .slice()
        .sort((a, b) => (a.order - b.order) || (b._seq - a._seq));
    },
  },

  methods: {
    // Resolve a block's component. Manifest blocks carry a component *name*
    // string; it must be resolved to the definition here because the tiles are
    // registered on the root app instance, not on this child. Runtime blocks
    // already carry the component object, which is returned as-is.
    blockComponent(component) {
      if (component && typeof component === 'object') return component;
      return (window.__vrgComponents && window.__vrgComponents[component]) || component;
    },

    async load() {
      this.loading = true;
      this.error = '';
      try {
        const response = await fetch('/api/dashboard/status', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) {
          this.error = (data && data.error) || this.$t('http.home.error_load');
        } else {
          this.dataByKey = data && typeof data === 'object' ? data : {};
        }
      } catch (err) {
        this.error = this.$t('http.common.error_connection');
      } finally {
        this.loading = false;
      }
    },
  },

  async mounted() {
    await this.load();
  },
};

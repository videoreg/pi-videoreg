// Dashboard tile: a single freshly captured media item, injected at runtime by
// DashboardCameraActionsTile after a photo/short-video capture. Not declared in
// the manifest — it is inserted imperatively (the actions tile passes this
// component object directly). It only needs to be bundled (listed in the
// camera plugin's http.components).
const DashboardMediaTile = {
  components: { TripsMediaItem },
  props: {
    data: { type: Object, default: null },
    loading: { type: Boolean, default: false },
  },

  template: `
    <div v-if="data && data.item" class="dashboard-tile dashboard-tile--media">
      <trips-media-item :item="data.item" :initial-video-ready="data.ready !== false"></trips-media-item>
    </div>
  `,
};

// Dashboard tile: quick capture actions (photo / night photo / short video).
// Interactive block — declares no data method. On a successful capture it
// injects a DashboardMediaTile block (order 25, just after this tile) via the
// host-provided `dashboard` API, passing the component object directly (it is
// bundled alongside this tile), so no manifest declaration is needed for it.
const DashboardCameraActionsTile = {
  components: { Icon },
  inject: ['dashboard'],
  props: {
    // Present for a uniform block interface; unused (no data method).
    data: { type: Object, default: null },
    loading: { type: Boolean, default: false },
  },

  template: `
    <div class="dashboard-tile" style="cursor: default;">
      <div class="dashboard-tile-header">
        <span class="dashboard-tile-icon"><icon name="camera" :size="20"></icon></span>
        <span class="dashboard-tile-title">{{ $t('http.home.actions_title') }}</span>
      </div>
      <div style="display: flex; gap: var(--spacing-sm); flex-wrap: wrap;">
        <button class="btn btn-outline btn-sm" @click="takePhoto(null)" :disabled="takingPhoto">
          {{ takingPhoto ? $t('http.app.taking_photo') : $t('http.app.take_photo') }}
        </button>
        <button class="btn btn-outline btn-sm" @click="takePhoto('night')" :disabled="takingPhoto">
          {{ $t('http.app.take_photo_night') }}
        </button>
        <button class="btn btn-outline btn-sm" @click="takeShortVideo()" :disabled="takingShortVideo">
          {{ takingShortVideo ? $t('http.app.taking_photo') : $t('http.app.take_short_video') }}
        </button>
      </div>
    </div>
  `,

  data() {
    return {
      takingPhoto: false,
      takingShortVideo: false,
    };
  },

  methods: {
    _nameToDatetime(name) {
      const [date, time] = name.split('_');
      return date + 'T' + time.replace(/-/g, ':');
    },

    _addMediaBlock(item) {
      this.dashboard.addBlock({
        key: 'camera:media:' + item.filename,
        component: DashboardMediaTile,
        order: 25,
        data: { item, ready: true },
      });
    },

    async takePhoto(mode) {
      if (this.takingPhoto) return;
      this.takingPhoto = true;
      try {
        const body = mode ? { mode, is_sync: true } : { is_sync: true };
        const response = await fetch('/api/camera/photo', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await response.json();
        if (!response.ok) return;
        this._addMediaBlock({ type: 'photo', filename: data.name + '.jpg', date: this._nameToDatetime(data.name) });
      } catch (err) {
        console.warn('Photo capture error', err);
      } finally {
        this.takingPhoto = false;
      }
    },

    async takeShortVideo() {
      if (this.takingShortVideo) return;
      this.takingShortVideo = true;
      try {
        const response = await fetch('/api/camera/short_video', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_sync: true }),
        });
        const data = await response.json();
        if (!response.ok) return;
        this._addMediaBlock({ type: 'video', filename: data.name + '.mp4', date: this._nameToDatetime(data.name) });
      } catch (err) {
        console.warn('Short video capture error', err);
      } finally {
        this.takingShortVideo = false;
      }
    },
  },
};

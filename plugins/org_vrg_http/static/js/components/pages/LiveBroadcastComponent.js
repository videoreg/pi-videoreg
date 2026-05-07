const LiveBroadcastComponent = {
  components: { Icon },

  props: {
    bgImageUrl: { type: String, default: null },
  },

  template: `
    <div>
      <div class="page-header">
        <h1 class="page-title">{{ $t('http.live.title') }}</h1>
        <button
          class="btn"
          :class="streaming ? 'btn-danger' : 'btn-primary'"
          @click="toggle"
          :disabled="busy"
        >
          {{ streaming ? $t('http.live.stop') : $t('http.live.start') }}
        </button>
      </div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div style="position:relative;width:100%;aspect-ratio:16/9;background:#000;border-radius:var(--border-radius-md);overflow:hidden;">
        <div v-if="bgImageUrl" style="position:absolute;inset:0;border-radius:var(--radius-md);overflow:hidden;">
          <img :src="bgImageUrl"
               style="width:100%;height:100%;object-fit:cover;filter:blur(16px) brightness(0.9);transform:scale(1.1);display:block;" />
        </div>
        <video ref="video" muted playsinline
               style="position:relative;z-index:1;width:100%;height:100%;object-fit:contain;display:block;"></video>
        <div v-if="starting" style="position:absolute;inset:0;z-index:2;display:flex;align-items:center;justify-content:center;color:var(--color-text-secondary);font-size:var(--font-size-sm);">
          {{ $t('http.live.starting') }}
        </div>
      </div>
    </div>
  `,

  data() {
    return {
      streaming: false,
      busy: false,
      starting: false,
      error: '',
      _hls: null,
      _retryTimer: null,
      _statusTimer: null,
      _unloadHandler: null,
      _pauseHandler: null,
    };
  },

  methods: {
    async toggle() {
      if (this.busy) return;
      this.busy = true;
      try {
        if (this.streaming) {
          await this.stop();
        } else {
          await this.start();
        }
      } finally {
        this.busy = false;
      }
    },

    async start() {
      this.error = '';
      this.starting = true;
      try {
        const r = await fetch('/api/camera/stream_start', {
          method: 'POST',
          credentials: 'same-origin',
        });
        if (!r.ok) {
          this.error = this.$t('http.live.error_start');
          await this.stop();
          return;
        }
        this.streaming = true;
        this._waitForPlaylist('/hls/stream.m3u8');
      } catch (e) {
        this.error = this.$t('http.live.error_start');
        this.starting = false;
      }
    },

    _waitForPlaylist(url) {
      let tries = 0;
      const tick = async () => {
        tries++;
        try {
          const h = await fetch(url, { method: 'HEAD', credentials: 'same-origin' });
          if (h.ok) {
            this._attach(url);
            this._startStatusPoll();
            this.starting = false;
            return;
          }
        } catch (e) {}
        if (tries < 30) {
          this._retryTimer = setTimeout(tick, 500);
        } else {
          this.error = this.$t('http.live.error_no_stream');
          await this.stop();
        }
      };
      tick();
    },

    _attach(url) {
      const video = this.$refs.video;
      if (!video) return;
      this._pauseHandler = () => { if (this.streaming) video.play(); };
      video.addEventListener('pause', this._pauseHandler);
      if (window.Hls && Hls.isSupported()) {
        this._hls = new Hls({ lowLatencyMode: true, liveSyncDuration: 2 });
        this._hls.loadSource(url);
        this._hls.attachMedia(video);
        this._hls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = url;
        video.play();
      }
    },

    _loadHls() {
      if (window.Hls) return Promise.resolve();
      return new Promise((resolve, reject) => {
        const s = document.createElement('script');
        s.src = '/static/js/vendor/hls.min.js';
        s.onload = resolve;
        s.onerror = reject;
        document.head.appendChild(s);
      });
    },

    _startStatusPoll() {
      this._stopStatusPoll();
      this._statusTimer = setInterval(async () => {
        if (!this.streaming) { this._stopStatusPoll(); return; }
        try {
          const r = await fetch('/api/camera/stream_status', { credentials: 'same-origin' });
          if (r.ok) {
            const body = await r.json();
            const d = body.data || body;
            if (!d.streaming && this.streaming) await this.stop();
          }
        } catch (e) {}
      }, 10000);
    },

    _stopStatusPoll() {
      if (this._statusTimer) {
        clearInterval(this._statusTimer);
        this._statusTimer = null;
      }
    },

    async stop(beacon = false) {
      this.starting = false;
      this._stopStatusPoll();
      if (this._retryTimer) {
        clearTimeout(this._retryTimer);
        this._retryTimer = null;
      }
      const video = this.$refs.video;
      if (video && this._pauseHandler) {
        video.removeEventListener('pause', this._pauseHandler);
        this._pauseHandler = null;
      }
      if (this._hls) {
        this._hls.destroy();
        this._hls = null;
      }
      if (video) {
        video.pause();
        video.src = '';
        video.load();
      }
      const url = '/api/camera/stream_stop';
      if (beacon && navigator.sendBeacon) {
        navigator.sendBeacon(url);
      } else {
        try {
          await fetch(url, { method: 'POST', credentials: 'same-origin', keepalive: true });
        } catch (e) {}
      }
      this.streaming = false;
    },
  },

  async mounted() {
    await this._loadHls();

    try {
      const r = await fetch('/api/camera/stream_status', { credentials: 'same-origin' });
      if (r.ok) {
        const body = await r.json();
        const d = body.data || body;
        if (d.streaming && d.hls_url) {
          this.streaming = true;
          this._attach(d.hls_url);
          this._startStatusPoll();
        }
      }
    } catch (e) {}

    this._unloadHandler = () => {
      if (this.streaming) this.stop(true);
    };
    window.addEventListener('pagehide', this._unloadHandler);
  },

  beforeUnmount() {
    if (this._unloadHandler) {
      window.removeEventListener('pagehide', this._unloadHandler);
    }
    if (this.streaming) this.stop();
  },
};

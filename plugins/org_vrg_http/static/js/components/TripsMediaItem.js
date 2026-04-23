// Компонент медиа-элемента на странице Поездок.
// Отображает превью фото или видео, тултип с действиями,
// управляет конвертацией H.264 → MP4.
//
// Prop item:
//   {
//     type: 'photo' | 'video',
//     filename: string,    // например "VID_001.h264" или "IMG_001.jpg"
//     date: string,        // ISO-дата
//     screenshot?: string  // только у видео: имя jpg-скриншота, например "VID_001.jpg"
//   }
const TripsMediaItem = {
  components: { Icon, Tooltip },

  props: {
    item: {
      type: Object,
      required: true
    },
    initialVideoReady: {
      type: Boolean,
      default: false
    },
    fave: {
      type: Boolean,
      default: false
    }
  },

  template: `
    <tooltip @close="onTooltipClose" style="height: 100%; display: block;">
      <template #anchor="{ open, close }">
        <div class="trips-media-item" @click="onTooltipOpen(open, close)" style="height: 100%;">
          <img
            v-if="item.type === 'photo'"
            :src="photoSrc"
            style="display: block; width: 100%; height: 100%; object-fit: cover;"
          />
          <img
            v-if="item.type === 'video' && item.screenshot"
            :src="photoBasePath + stripExt(item.screenshot)"
            style="display: block; width: 100%; height: 100%; object-fit: cover;"
          />
          <div class="trips-media-badge">
            <icon :name="item.type === 'photo' ? 'camera' : 'video'" :size="14"></icon>
            <span>{{ timeLabel }}</span>
          </div>
        </div>
      </template>

      <div class="trips-media-tooltip-header">
        <icon :name="item.type === 'photo' ? 'camera' : 'video'" :size="16"></icon>
        <span class="trips-media-tooltip-filename">{{ item.filename }}</span>
      </div>
      <hr class="tooltip-divider">

      <button
        v-if="item.type === 'photo'"
        class="tooltip-btn"
        @click="openPhoto"
      >{{ $t('http.media_item.open_image') }}</button>

      <button
        v-if="item.type === 'video' && item.screenshot"
        class="tooltip-btn"
        @click="openScreenshot"
      >{{ $t('http.media_item.download_screenshot') }}</button>

      <a
        v-if="item.type === 'video' && videoReady"
        class="tooltip-btn"
        :href="'/video/' + name"
        target="_blank"
        rel="noopener"
      >{{ $t('http.media_item.download_mp4') }}</a>
      <button
        v-else-if="item.type === 'video'"
        class="tooltip-btn"
        @click="clickDownloadMp4"
      >{{ converting ? $t('http.media_item.converting') : $t('http.media_item.download_mp4') }}</button>

      <button
        v-if="!fave"
        class="tooltip-btn"
        :class="{ 'tooltip-btn--success': isFaved }"
        @click="toggleFave"
      >{{ isFaved ? $t('http.media_item.in_fave') : $t('http.media_item.add_to_fave') }}</button>
    </tooltip>
  `,

  data() {
    return {
      videoReady: this.initialVideoReady,
      converting: false,
      tooltipOpen: false,
      tooltipCloseFn: null,
      _pollTimer: null,
      _checkAbort: null,
      isFaved: false
    };
  },

  computed: {
    name() {
      return this.stripExt(this.item.filename);
    },
    timeLabel() {
      if (!this.item.date) return '—';
      try {
        const d = new Date(this.item.date);
        return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
      } catch (e) {
        return this.item.date;
      }
    },
    photoBasePath() {
      return this.fave ? '/fave_photo/' : '/photo/';
    },
    photoSrc() {
      if (this.item.type !== 'photo') return '';
      return this.photoBasePath + this.name;
    }
  },

  methods: {
    stripExt(filename) {
      const lastDot = filename.lastIndexOf('.');
      return lastDot > 0 ? filename.slice(0, lastDot) : filename;
    },

    onTooltipOpen(openFn, closeFn) {
      openFn();
      this.tooltipOpen = true;
      this.tooltipCloseFn = closeFn;
      if (this.item.type === 'video') {
        if (this.converting) {
          this._startPoll();
        } else if (!this.videoReady) {
          this._checkAndUpdateReady();
        }
      }
    },

    onTooltipClose() {
      this.tooltipOpen = false;
      this._stopPoll();
      this._abortCheck();
    },

    openPhoto() {
      window.open(this.photoSrc, '_blank');
      if (this.tooltipCloseFn) {
        this.tooltipCloseFn();
      }
    },

    async toggleFave() {
      const method = this.isFaved ? 'DELETE' : 'POST';
      const baseName = this.name;
      const type = this.item.type === 'video' ? 'h264' : 'jpeg';
      try {
        await fetch('/api/camera/fave', {
          method,
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ type, name: baseName })
        });
        this.isFaved = !this.isFaved;
        this.$emit('fave-changed', { name: baseName, faved: this.isFaved });
      } catch (err) {
        console.warn('Ошибка при изменении избранного', err);
      }
    },

    openScreenshot() {
      window.open(this.photoBasePath + this.stripExt(this.item.screenshot), '_blank');
    },

    async clickDownloadMp4() {
      if (this.converting) {
        // Ручная проверка во время конвертации — только обновляем UI
        await this._checkAndUpdateReady();
        if (this.videoReady) {
          this._stopPoll();
          this.converting = false;
        }
        return;
      }
      // Показываем "Конвертация..." сразу, не ожидая ответа сервера
      this.converting = true;
      await this._checkAndUpdateReady();
      if (this.videoReady) {
        // Файл уже готов — убираем converting, шаблон покажет <a>
        this.converting = false;
        return;
      }
      await this._startConvert();
    },

    async _checkVideoReady(signal) {
      try {
        const resp = await fetch(
          `/api/camera/convert_check?name=${encodeURIComponent(this.name)}`,
          { credentials: 'same-origin', signal }
        );
        const data = await resp.json();
        return data.ready === true;
      } catch (e) {
        if (e.name === 'AbortError') return null;
        return false;
      }
    },

    async _checkAndUpdateReady() {
      this._abortCheck();
      this._checkAbort = new AbortController();
      const ready = await this._checkVideoReady(this._checkAbort.signal);
      if (ready !== null) {
        this.videoReady = ready;
      }
    },

    _abortCheck() {
      if (this._checkAbort) {
        this._checkAbort.abort();
        this._checkAbort = null;
      }
    },

    async _startConvert() {
      try {
        const resp = await fetch('/api/camera/convert', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: this.name }),
          credentials: 'same-origin'
        });
        const data = await resp.json();
        if (data.message === 'already_ready') {
          this.videoReady = true;
          this.converting = false;
          return;
        }
        this.converting = true;
        this._startPoll();
      } catch (e) {
        // ignore
      }
    },

    _startPoll() {
      this._stopPoll();
      this._pollTimer = setInterval(async () => {
        if (!this.tooltipOpen) {
          this._stopPoll();
          return;
        }
        const ready = await this._checkVideoReady();
        if (ready) {
          this._stopPoll();
          this.converting = false;
          this.videoReady = true;
        }
      }, 5000);
    },

    _stopPoll() {
      if (this._pollTimer) {
        clearInterval(this._pollTimer);
        this._pollTimer = null;
      }
    }
  },

  beforeUnmount() {
    this._stopPoll();
    this._abortCheck();
  }
};

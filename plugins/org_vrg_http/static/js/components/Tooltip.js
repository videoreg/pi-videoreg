// Переиспользуемый компонент тултипа
// Позиционируется автоматически (сверху или снизу якоря),
// горизонтально центрируется, не выходит за рамки экрана.
//
// Использование:
//   <tooltip ref="myTooltip">
//     <template #anchor="{ open, close }">
//       <span @click="open">Якорь</span>
//     </template>
//     <template #default>
//       Содержимое тултипа
//     </template>
//   </tooltip>
const Tooltip = {
  template: `
    <div class="tooltip-anchor" ref="anchor">
      <slot name="anchor" :open="openTooltip" :close="close"></slot>
      <teleport to="body">
        <div v-if="visible && isSheet" class="tooltip-sheet-overlay" @click="close"></div>
        <div
          v-if="visible"
          class="tooltip-popup"
          :class="{ 'tooltip-popup--sheet': isSheet }"
          ref="popup"
          :style="isSheet ? {} : popupStyle"
          @click.stop
        >
          <slot></slot>
        </div>
      </teleport>
    </div>
  `,

  data() {
    return {
      visible: false,
      popupStyle: {},
      isSheet: false,
      _outsideHandler: null
    };
  },

  methods: {
    openTooltip(event) {
      if (this.visible) {
        this.close();
        return;
      }
      this.visible = true;
      // Позиционируем после рендера
      this.$nextTick(() => {
        this._position();
        this._bindOutside();
      });
    },

    close() {
      this.visible = false;
      this._unbindOutside();
      this.$emit('close');
    },

    _position() {
      this.isSheet = window.innerWidth <= 768;
      if (this.isSheet) return;

      const anchor = this.$refs.anchor;
      const popup = this.$refs.popup;
      if (!anchor || !popup) return;

      const anchorRect = anchor.getBoundingClientRect();
      const popupRect = popup.getBoundingClientRect();
      const vpW = window.innerWidth;
      const vpH = window.innerHeight;
      const margin = 12;

      // Ширина тултипа (не выходим за экран)
      const maxWidth = vpW - margin * 2;
      const popupW = Math.min(popupRect.width, maxWidth);

      // Горизонтальное центрирование относительно якоря
      let left = anchorRect.left + anchorRect.width / 2 - popupW / 2;
      // Зажимаем в рамки экрана
      if (left < margin) left = margin;
      if (left + popupW > vpW - margin) left = vpW - margin - popupW;

      // Вертикаль: предпочтительно снизу, если нет места — сверху
      const spaceBelow = vpH - anchorRect.bottom - margin;
      const spaceAbove = anchorRect.top - margin;
      const gap = 6;
      let top;
      if (spaceBelow >= popupRect.height || spaceBelow >= spaceAbove) {
        top = anchorRect.bottom + gap;
      } else {
        top = anchorRect.top - gap - popupRect.height;
      }

      this.popupStyle = {
        position: 'fixed',
        top: Math.round(top) + 'px',
        left: Math.round(left) + 'px',
        width: Math.round(popupW) + 'px'
      };
    },

    _bindOutside() {
      this._outsideHandler = (e) => {
        const anchor = this.$refs.anchor;
        const popup = this.$refs.popup;
        if (anchor && anchor.contains(e.target)) return;
        if (popup && popup.contains(e.target)) return;
        this.close();
      };
      document.addEventListener('click', this._outsideHandler, true);
    },

    _unbindOutside() {
      if (this._outsideHandler) {
        document.removeEventListener('click', this._outsideHandler, true);
        this._outsideHandler = null;
      }
    }
  },

  beforeUnmount() {
    this._unbindOutside();
  }
};

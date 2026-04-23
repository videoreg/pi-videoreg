// Переиспользуемый компонент полосы прогресса
const ProgressBar = Vue.defineComponent({
  name: 'ProgressBar',

  props: {
    value: {
      type: Number,
      required: true
    },
    showLabel: {
      type: Boolean,
      default: true
    },
    variant: {
      type: String,
      default: 'auto'
    },
    thresholds: {
      type: Object,
      default: () => ({ warning: 70, critical: 85 })
    }
  },

  computed: {
    fillClass() {
      let v = this.variant;
      if (v === 'auto') {
        if (this.value >= this.thresholds.critical) {
          v = 'critical';
        } else if (this.value >= this.thresholds.warning) {
          v = 'warning';
        } else {
          v = 'normal';
        }
      }
      if (v === 'warning') return 'progress-fill--warning';
      if (v === 'critical') return 'progress-fill--critical';
      return '';
    }
  },

  template: `
    <div class="progress-bar">
      <div class="progress-track">
        <div class="progress-fill" :class="fillClass" :style="{ width: value + '%' }"></div>
      </div>
      <span v-if="showLabel" class="progress-label">{{ value }}%</span>
    </div>
  `
});

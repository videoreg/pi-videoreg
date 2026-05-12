const Shimmer = {
  props: {
    width:  { type: String, default: '100%' },
    height: { type: String, default: '1em' },
  },
  template: `<span class="shimmer" :style="{ width, height }"></span>`,
};

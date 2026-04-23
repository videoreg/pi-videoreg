// Компонент переключателя в стиле iOS
const ToggleSwitch = {
  template: `
    <label class="toggle-switch">
      <input 
        type="checkbox" 
        :checked="modelValue"
        @change="$emit('update:modelValue', $event.target.checked)"
        :disabled="disabled"
      />
      <span class="toggle-slider"></span>
      <span class="toggle-label" v-if="label">{{ label }}</span>
    </label>
  `,
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    disabled: {
      type: Boolean,
      default: false
    },
    label: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue']
};

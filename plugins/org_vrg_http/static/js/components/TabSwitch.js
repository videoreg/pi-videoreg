// Компонент переключателя вкладок
const TabSwitch = {
  template: `
    <div class="tab-switch">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        class="tab-button"
        :class="{ 'active': modelValue === tab.value }"
        @click="$emit('update:modelValue', tab.value)"
        :disabled="disabled"
      >
        {{ tab.label }}
      </button>
    </div>
  `,
  props: {
    modelValue: {
      type: String,
      required: true
    },
    tabs: {
      type: Array,
      required: true,
      // Формат: [{ value: 'status', label: 'Статус' }, { value: 'settings', label: 'Настройка' }]
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:modelValue']
};

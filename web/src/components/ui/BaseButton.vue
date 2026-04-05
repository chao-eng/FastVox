<script setup lang="ts">
import { computed } from 'vue';
const props = withDefaults(defineProps<{
  type?: 'primary' | 'secondary' | 'text' | 'danger';
  loading?: boolean;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
}>(), {
  type: 'secondary',
  loading: false,
  disabled: false,
  size: 'md'
});

const emit = defineEmits(['click']);

const classes = computed(() => [
  'btn',
  `btn-${props.type}`,
  `btn-s-${props.size}`,
  { 'is-loading': props.loading, 'is-disabled': props.disabled || props.loading }
]);
</script>

<template>
  <button :class="classes" :disabled="disabled || loading" @click="emit('click')">
    <span v-if="loading" class="spinner"></span>
    <slot></slot>
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-medium);
  font-size: 14px;
  cursor: pointer;
  transition: var(--transition);
  outline: none;
  gap: 8px;
  white-space: nowrap;
}

.btn-s-md { height: 36px; padding: 0 16px; }
.btn-s-sm { height: 32px; padding: 0 12px; font-size: 12px; }
.btn-s-lg { height: 44px; padding: 0 24px; font-size: 16px; }

/* 飞书 Primary 蓝 */
.btn-primary {
  background-color: var(--color-primary);
  color: white;
}
.btn-primary:hover { background-color: var(--color-primary-hover); transform: translateY(-1px); }
.btn-primary:active { background-color: var(--color-primary-active); transform: translateY(0); }

/* Secondary 幽灵边框 */
.btn-secondary {
  border-color: var(--color-border);
  background-color: white;
  color: var(--color-text-primary);
}
.btn-secondary:hover { border-color: var(--color-primary); color: var(--color-primary); background-color: var(--color-primary-light); }

/* Text 模式 */
.btn-text {
  background: transparent;
  color: var(--color-text-secondary);
}
.btn-text:hover { color: var(--color-primary); background-color: var(--color-primary-light); }

.is-disabled {
  opacity: 0.5;
  cursor: not-allowed !important;
  transform: none !important;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

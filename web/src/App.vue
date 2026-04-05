<script setup lang="ts">
// 全局入口，主要处理路由视图切换
</script>

<template>
  <router-view v-if="$route.meta.layout === 'none'"></router-view>
  <router-view v-else></router-view>
</template>

<style>
/* 可以在此处添加全局动画，如 Fade Transition */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

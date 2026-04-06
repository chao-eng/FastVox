<script setup lang="ts">
import { Settings, Shield, Zap, Bell, Database } from 'lucide-vue-next';
import BaseButton from '../components/ui/BaseButton.vue';
</script>

<template>
  <div class="settings-view">
    <div class="header">
      <h2>系统设置</h2>
      <p>管理 FastVox 核心推理参数与安全策略</p>
    </div>

    <div class="grid">
      <div class="card">
        <div class="card-title">
          <Zap :size="20" /> <span>性能参数</span>
        </div>
        <div class="field">
          <label>默认推理线程数</label>
          <input type="number" value="4" class="input" />
        </div>
        <BaseButton type="primary" size="sm">保存更改</BaseButton>
      </div>

      <div class="card">
        <div class="card-title">
          <Shield :size="20" /> <span>安全 / API</span>
        </div>
        <div class="field">
          <label>JWT 有效时长 (秒)</label>
          <input type="number" value="86400" class="input" />
        </div>
        <BaseButton type="primary" size="sm">更新策略</BaseButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-view { max-width: 1000px; }
.header { margin-bottom: 32px; }
.header h2 { font-size: 24px; font-weight: 600; margin-bottom: 8px; }
.header p { color: var(--color-text-secondary); font-size: 14px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; }
.card { background: var(--color-bg-card); padding: 24px; border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-sm); }
.card-title { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; font-weight: 600; color: var(--color-text-primary); }
.field { margin-bottom: 20px; }
.field label { display: block; font-size: 13px; color: var(--color-text-secondary); margin-bottom: 8px; }
.input { width: 100%; height: 36px; border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 0 12px; outline: none; background: var(--color-bg-card); color: var(--color-text-primary); }
</style>

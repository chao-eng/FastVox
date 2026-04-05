<script setup lang="ts">
import { ref } from 'vue';
import { Settings, Shield, Bell, Zap, Database, Save } from 'lucide-vue-next';
import BaseButton from '../components/ui/BaseButton.vue';

const activeTab = ref('general');

const tabs = [
  { id: 'general', name: '首选项', icon: Settings },
  { id: 'inference', name: '推理引擎', icon: Zap },
  { id: 'storage', name: '存储管理', icon: Database },
  { id: 'security', name: '安全中心', icon: Shield },
  { id: 'notifications', name: '通知设置', icon: Bell },
];

const settings = ref({
  apiEndpoint: 'http://localhost:8000',
  apiKey: '********-****-****-****-************',
  autoSave: true,
  maxConcurrency: 4,
  modelCacheSize: 2048,
  theme: 'light',
  exportFormat: 'wav',
});

const handleSave = () => {
  // 模拟保存逻辑
  console.log('Saving settings:', settings.value);
};
</script>

<template>
  <div class="settings-view">
    <div class="settings-container">
      <!-- 侧边导航 -->
      <aside class="settings-nav">
        <div 
          v-for="tab in tabs" 
          :key="tab.id"
          :class="['nav-item', { active: activeTab === tab.id }]"
          @click="activeTab = tab.id"
        >
          <component :is="tab.icon" :size="18" />
          <span>{{ tab.name }}</span>
        </div>
      </aside>

      <!-- 内容区 -->
      <main class="settings-content">
        <div class="content-header">
          <h2>{{ tabs.find(t => t.id === activeTab)?.name }}</h2>
          <p>更新您的系统配置并管理服务连接。</p>
        </div>

        <div v-if="activeTab === 'general'" class="settings-form">
          <div class="setting-group">
            <div class="setting-row">
              <div class="setting-info">
                <label>API 端点</label>
                <p>后端服务的基础 URL 地址。</p>
              </div>
              <input type="text" v-model="settings.apiEndpoint" class="input" />
            </div>

            <div class="setting-row">
              <div class="setting-info">
                <label>API 密钥</label>
                <p>用于身份验证的服务密钥。</p>
              </div>
              <input type="password" v-model="settings.apiKey" class="input" />
            </div>

            <div class="setting-row">
              <div class="setting-info">
                <label>自动保存</label>
                <p>在修改配置后自动同步到服务器。</p>
              </div>
              <label class="switch">
                <input type="checkbox" v-model="settings.autoSave" />
                <span class="slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-group">
            <h3>导出设置</h3>
            <div class="setting-row">
              <div class="setting-info">
                <label>音频格式</label>
                <p>默认生成的音频文件格式。</p>
              </div>
              <select v-model="settings.exportFormat" class="select">
                <option value="wav">WAV (无损)</option>
                <option value="mp3">MP3 (高压缩)</option>
                <option value="ogg">OGG (Opus)</option>
              </select>
            </div>
          </div>
        </div>

        <div v-else class="placeholder">
          <div class="icon-box">
            <component :is="tabs.find(t => t.id === activeTab)?.icon" :size="48" />
          </div>
          <p>此模块正在动态加载中...</p>
        </div>

        <footer class="content-footer">
          <BaseButton type="primary" size="lg" @click="handleSave">
            <Save :size="18" /> 保存更改
          </BaseButton>
        </footer>
      </main>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  width: 100%;
}

.settings-container {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 40px;
  background: white;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  min-height: 600px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.settings-nav {
  background: var(--color-bg-page);
  border-right: 1px solid var(--color-border);
  padding: 24px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition);
  font-size: 14px;
  font-weight: 500;
}

.nav-item:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--color-text-primary);
}

.nav-item.active {
  background: white;
  color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.settings-content {
  padding: 40px;
  display: flex;
  flex-direction: column;
}

.content-header {
  margin-bottom: 32px;
}

.content-header h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--color-text-primary);
}

.content-header p {
  color: var(--color-text-secondary);
  font-size: 14px;
}

.settings-form {
  flex: 1;
}

.setting-group {
  margin-bottom: 32px;
}

.setting-group h3 {
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-text-disabled);
  margin-bottom: 20px;
  letter-spacing: 0.05em;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 0;
  border-bottom: 1px solid var(--color-bg-page);
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-info label {
  display: block;
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.setting-info p {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.input, .select {
  width: 240px;
  height: 36px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 0 12px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.input:focus, .select:focus {
  border-color: var(--color-primary);
}

.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--color-border);
  transition: .4s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: var(--color-primary);
}

input:checked + .slider:before {
  transform: translateX(20px);
}

.content-footer {
  margin-top: 40px;
  padding-top: 24px;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
}

.placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-disabled);
  gap: 16px;
}

.icon-box {
  width: 80px;
  height: 80px;
  background: var(--color-bg-page);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>

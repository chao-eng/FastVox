<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Plus, Trash2, Save } from 'lucide-vue-next';
import BaseButton from '../components/ui/BaseButton.vue';
import client from '../api/client';

interface AppConfig {
  id?: string;
  appid: string;
  appsecret: string;
  app_name: string;
  is_active: boolean;
}

const configs = ref<AppConfig[]>([]);
const isLoading = ref(false);

const fetchConfigs = async () => {
  isLoading.value = true;
  try {
    // 使用统一的 client 会自动处理项目前缀和 Token
    configs.value = await client.get('/admin/config');
  } catch (err) {
    console.error('Failed to fetch configs:', err);
  } finally {
    isLoading.value = false;
  }
};

const addConfig = () => {
  configs.value.push({
    appid: '',
    appsecret: '',
    app_name: '新小程序',
    is_active: true
  });
};

const saveConfig = async (config: AppConfig) => {
  try {
    await client.post('/admin/config', config);
    alert('保存成功');
    fetchConfigs();
  } catch (err) {
    alert('保存失败');
  }
};

const deleteConfig = async (id: string, index: number) => {
  if (!id) {
    configs.value.splice(index, 1);
    return;
  }
  
  if (!confirm('确定删除该配置吗？')) return;

  try {
    await client.delete(`/admin/config/${id}`);
    fetchConfigs();
  } catch (err) {
    alert('删除失败');
  }
};

onMounted(fetchConfigs);
</script>

<template>
  <div class="settings-view">
    <div class="header">
      <div class="title-row">
        <h2>微信小程序管理</h2>
        <BaseButton type="primary" size="sm" @click="addConfig">
          <Plus :size="16" /> <span>新增配置</span>
        </BaseButton>
      </div>
      <p>管理多个微信小程序接入，配置对应的 AppID 与 AppSecret</p>
    </div>

    <div class="config-list">
      <div v-if="configs.length === 0 && !isLoading" class="empty-state">
        暂无小程序配置，请点击右上角新增
      </div>

      <div v-for="(config, index) in configs" :key="config.id || index" class="config-card">
        <div class="card-body">
          <div class="input-group">
            <label>应用名称</label>
            <input v-model="config.app_name" placeholder="例如：FastVox 语音助" class="input" />
          </div>
          <div class="input-grid">
            <div class="input-group">
              <label>AppID</label>
              <input v-model="config.appid" placeholder="wx123456..." class="input" />
            </div>
            <div class="input-group">
              <label>AppSecret</label>
              <input v-model="config.appsecret" type="password" placeholder="密钥" class="input" />
            </div>
          </div>
        </div>
        <div class="card-actions">
          <BaseButton type="secondary" size="sm" @click="deleteConfig(config.id!, index)">
            <Trash2 :size="16" />
          </BaseButton>
          <BaseButton type="primary" size="sm" @click="saveConfig(config)">
            <Save :size="16" /> <span>保存配置</span>
          </BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-view { max-width: 1200px; padding: 20px; }
.header { margin-bottom: 32px; }
.title-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.header h2 { font-size: 24px; font-weight: 600; }
.header p { color: var(--color-text-secondary); font-size: 14px; }

.config-list { display: grid; gap: 20px; }
.config-card { 
  background: var(--color-bg-card); 
  border-radius: var(--radius-lg); 
  border: 1px solid var(--color-border); 
  overflow: hidden;
  transition: all 0.2s;
}
.config-card:hover { border-color: var(--color-primary-light); box-shadow: var(--shadow-md); }

.card-body { padding: 24px; }
.input-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 16px; }
.input-group { display: flex; flex-direction: column; gap: 8px; }
.input-group label { font-size: 13px; font-weight: 500; color: var(--color-text-secondary); }

.input { 
  width: 100%; 
  height: 40px; 
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 0 12px;
  color: var(--color-text-primary);
  outline: none;
}
.input:focus { border-color: var(--color-primary); }

.card-actions { 
  background: rgba(0, 0, 0, 0.1); 
  padding: 12px 24px; 
  display: flex; 
  justify-content: flex-end; 
  gap: 12px; 
  border-top: 1px solid var(--color-border);
}

.empty-state {
  text-align: center;
  padding: 60px;
  color: var(--color-text-secondary);
  background: var(--color-bg-card);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
}
</style>

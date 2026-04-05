<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { 
  MessageSquare, 
  Mic2, 
  Settings2, 
  BarChart2, 
  LogOut,
  ChevronLeft,
  ChevronRight,
  Sun,
  Moon
} from 'lucide-vue-next';

const router = useRouter();
const route = useRoute();
const isCollapsed = ref(false);

const navItems = [
  { name: '语音合成', path: '/', icon: MessageSquare },
  { name: '我的声纹', path: '/voices', icon: Mic2 },
  { name: '使用统计', path: '/stats', icon: BarChart2 },
  { name: '系统设置', path: '/settings', icon: Settings2 },
];

const navigate = (path: string) => router.push(path);
const toggleSidebar = () => isCollapsed.value = !isCollapsed.value;
</script>

<template>
  <div class="layout">
    <aside :class="['sidebar', { collapsed: isCollapsed }]">
      <div class="logo">
        <div class="logo-box">V</div>
        <span v-if="!isCollapsed" class="logo-text">FastVox</span>
      </div>

      <nav class="nav">
        <div 
          v-for="item in navItems" 
          :key="item.path"
          :class="['nav-item', { active: route.path === item.path }]"
          @click="navigate(item.path)"
        >
          <component :is="item.icon" :size="20" />
          <span v-if="!isCollapsed">{{ item.name }}</span>
        </div>
      </nav>

      <div class="footer">
        <div class="footer-item" @click="toggleSidebar">
          <component :is="isCollapsed ? ChevronRight : ChevronLeft" :size="20" />
          <span v-if="!isCollapsed">收起侧栏</span>
        </div>
      </div>
    </aside>

    <main class="main">
      <header class="header">
        <div class="breadcrumb">
          {{ navItems.find(i => i.path === route.path)?.name || '系统' }}
        </div>
        <div class="user">
          <button class="theme-toggle"><Sun :size="18" /></button>
          <div class="avatar">U</div>
        </div>
      </header>

      <div class="page-content" data-autofill="ignore">
        <router-view></router-view>
      </div>
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.sidebar {
  width: 240px;
  background-color: white;
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 20px 12px;
}

.sidebar.collapsed { width: 72px; padding: 20px 16px; }

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 8px 32px;
  font-weight: var(--font-weight-bold);
  font-size: 20px;
  color: var(--color-primary);
}

.logo-box {
  width: 32px;
  height: 32px;
  background: var(--color-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  flex-shrink: 0;
}

.nav { flex: 1; display: flex; flex-direction: column; gap: 4px; }

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition);
  font-weight: var(--font-weight-medium);
  font-size: 14px;
}

.nav-item:hover { background-color: var(--color-bg-page); color: var(--color-text-primary); }
.nav-item.active { background-color: var(--color-primary-light); color: var(--color-primary); }

.sidebar.collapsed .nav-item { justify-content: center; padding: 12px; }

.footer { padding-top: 12px; border-top: 1px solid var(--color-border); }
.footer-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.main { flex: 1; display: flex; flex-direction: column; background-image: radial-gradient(var(--color-border) 1px, transparent 0); background-size: 40px 40px; background-position: -19px -19px; }

.header {
  height: 60px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.breadcrumb { font-weight: var(--font-weight-semibold); font-size: 16px; }

.user { display: flex; align-items: center; gap: 16px; }
.theme-toggle { background: transparent; border: none; color: var(--color-text-secondary); cursor: pointer; }
.avatar { width: 32px; height: 32px; background: #E5E6EB; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; }

.page-content { flex: 1; padding: 32px; overflow-y: auto; max-width: 1200px; width: 100%; margin: 0 auto; }
</style>

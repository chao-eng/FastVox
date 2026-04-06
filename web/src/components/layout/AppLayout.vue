<script setup lang="ts">
import { ref, onMounted } from 'vue';
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
import client from '../../api/client';

const router = useRouter();
const route = useRoute();
const isCollapsed = ref(false);
const userName = ref('Guest');
const isDark = ref(localStorage.getItem('theme') === 'dark');

// 初始化主题
onMounted(async () => {
  if (isDark.value) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }

  try {
    const user: any = await client.get('/users/me');
    userName.value = user.nickname || user.email;
  } catch (err) {
    console.error('Failed to fetch user:', err);
  }
});

const toggleTheme = () => {
  isDark.value = !isDark.value;
  const theme = isDark.value ? 'dark' : 'light';
  localStorage.setItem('theme', theme);
  if (isDark.value) {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
};

const navItems = [
  { name: '语音合成', path: '/', icon: MessageSquare },
  { name: '我的声纹', path: '/voices', icon: Mic2 },
  { name: '使用统计', path: '/stats', icon: BarChart2 },
  { name: '系统设置', path: '/settings', icon: Settings2 },
];

const navigate = (path: string) => router.push(path);
const toggleSidebar = () => isCollapsed.value = !isCollapsed.value;

const handleLogout = () => {
  localStorage.removeItem('fastvox_token');
  router.push('/login');
};
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
          <button class="theme-toggle" @click="toggleTheme">
            <Sun v-if="!isDark" :size="18" />
            <Moon v-else :size="18" />
          </button>
          <div class="user-profile" :title="userName">
            <div class="avatar-circle">
              {{ userName.charAt(0).toUpperCase() }}
            </div>
            <span class="user-name">
              {{ userName.length > 6 ? userName.substring(0, 6) : userName }}
            </span>
          </div>
          <button class="logout-btn" title="退出登录" @click="handleLogout">
            <LogOut :size="18" />
          </button>
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
  background-color: var(--color-bg-card);
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
  background: var(--color-bg-card);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.breadcrumb { font-weight: var(--font-weight-semibold); font-size: 16px; }

.user { display: flex; align-items: center; gap: 20px; }
.theme-toggle { background: transparent; border: none; color: var(--color-text-secondary); cursor: pointer; transition: color 0.2s; }
.theme-toggle:hover { color: var(--color-primary); }

.user-profile { display: flex; align-items: center; gap: 10px; padding: 4px 12px 4px 4px; background: var(--color-bg-page); border-radius: 20px; transition: all 0.2s; border: 1px solid transparent; cursor: default; }
.user-profile:hover { background: var(--color-border); border-color: var(--color-border); }

.avatar-circle { width: 28px; height: 28px; background: var(--color-primary); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.user-name { font-size: 13px; font-weight: 500; color: var(--color-text-primary); max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.logout-btn { background: transparent; border: none; color: var(--color-text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; padding: 6px; border-radius: 6px; }
.logout-btn:hover { color: #F53F3F; background: #FFF1F0; }

.page-content { flex: 1; padding: 32px; overflow-y: auto; max-width: 1200px; width: 100%; margin: 0 auto; }
</style>

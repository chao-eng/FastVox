import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';
import AppLayout from '../components/layout/AppLayout.vue';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { layout: 'none' }
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'Synthesis',
        component: () => import('../views/SynthesisView.vue')
      },
      {
        path: 'voices',
        name: 'Voices',
        component: () => import('../views/VoiceView.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'stats',
        name: 'Stats',
        component: () => import('../views/StatsView.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../views/SettingsView.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/UsersView.vue'),
        meta: { requiresAdmin: true }
      }
    ]
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

import client from '../api/client';

// 路由守卫: 自动附带权限校验
router.beforeEach(async (to, from, next) => {
  const token = localStorage.getItem('fastvox_token');
  
  // 1. 登录跳转逻辑
  if (to.name !== 'Login' && !token) {
    return next({ name: 'Login' });
  }
  if (to.name === 'Login' && token) {
    return next({ name: 'Synthesis' });
  }

  // 2. 权限校验逻辑 (Admin Required)
  if (to.meta.requiresAdmin) {
    try {
      const user: any = await client.get('/users/me');
      if (!user.is_superuser) {
        alert('权限不足，仅管理员可访问同步页面');
        return next({ name: 'Synthesis' });
      }
    } catch (err) {
      return next({ name: 'Login' });
    }
  }

  next();
});

export default router;

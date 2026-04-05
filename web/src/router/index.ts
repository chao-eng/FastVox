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
        component: () => import('../views/VoiceView.vue')
      },
      {
        path: 'stats',
        name: 'Stats',
        component: () => import('../views/StatsView.vue')
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../views/SettingsView.vue')
      }
    ]
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 简单的路由守卫 (此处可集成 Token 校验)
router.beforeEach((to, from, next) => {
  const isAuthenticated = true; # 模拟已登录
  if (to.name !== 'Login' && !isAuthenticated) next({ name: 'Login' });
  else next();
});

export default router;

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Github, Mail, Lock, Loader2, ShieldCheck } from 'lucide-vue-next';
import BaseButton from '../components/ui/BaseButton.vue';
import client from '../api/client';

const router = useRouter();
const email = ref('');
const password = ref('');
const isLoading = ref(false);
const needSetup = ref(false);

// 检查初始化状态
const checkSetup = async () => {
  try {
    const res: any = await client.get('/auth/setup-status');
    needSetup.value = res.need_setup;
  } catch (e) {
    console.error('Setup check failed', e);
  }
};

const handleAction = async () => {
  if (!email.value || !password.value) return;
  isLoading.value = true;
  
  try {
    if (needSetup.value) {
      // 执行系统初始化
      await client.post('/auth/initial-setup', {
        email: email.value,
        password: password.value,
      });
      alert('系统初始化成功！请使用刚创建的账号登录。');
      needSetup.value = false;
    } else {
      // 执行正常登录
      const formData = new URLSearchParams();
      formData.append('username', email.value);
      formData.append('password', password.value);
      
      const res: any = await client.post('/auth/jwt/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      localStorage.setItem('fastvox_token', res.access_token);
      router.push('/');
    }
  } catch (err: any) {
    alert(err.response?.data?.detail || '操作失败，请重试');
  } finally {
    isLoading.value = false;
  }
};

onMounted(checkSetup);
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="header">
        <div class="logo-circle">V</div>
        <h1 v-show="needSetup">初始化 FastVox</h1>
        <h1 v-show="!needSetup">欢迎使用 FastVox</h1>
        <p v-show="needSetup">检测到系统首次运行，请设置您的管理员账户</p>
        <p v-show="!needSetup">高性能 TTS 与 In-context Learning 声音克隆系统</p>
      </div>

      <form class="form" @submit.prevent="handleAction">
        <div class="form-item">
          <label for="email">管理员邮箱</label>
          <div class="input-container">
            <Mail :size="16" class="icon" />
            <input 
              id="email"
              name="email"
              v-model="email" 
              type="email" 
              placeholder="请输入您的邮箱" 
              required 
              autocomplete="username"
            />
          </div>
        </div>

        <div class="form-item">
          <div class="label-row">
            <label for="password">密码</label>
            <a v-show="!needSetup" href="#" class="forgot-link">忘记密码？</a>
          </div>
          <div class="input-container">
            <Lock :size="16" class="icon" />
            <input 
              id="password"
              name="password"
              v-model="password" 
              type="password" 
              placeholder="建议输入 8 位以上强密码" 
              required
              autocomplete="current-password"
            />
          </div>
        </div>

        <BaseButton 
          type="primary" 
          size="lg" 
          native-type="submit"
          style="width: 100%; margin-top: 12px"
          :loading="isLoading"
        >
          {{ needSetup ? '初始化并创建账户' : '登 录' }}
        </BaseButton>
      </form>

      <div v-show="!needSetup">
        <div class="divider">
          <span>第三方登录</span>
        </div>
        <div class="social-login">
          <button class="social-btn"><Github :size="20" /></button>
          <button class="social-btn wechat">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8.5 13c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zm7 0c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zM22 10.5C22 5.81 17.52 2 12 2S2 5.81 2 10.5c0 2.5 1.25 4.74 3.25 6.25L4 21c4.5-1 4.5-1 6-1.5.65.16 1.32.25 2 .25 5.52 0 10-3.81 10-8.25z"/>
            </svg>
          </button>
        </div>
      </div>

      <div class="footer" v-show="!needSetup">
        还没有账号？ <a href="#">立即注册</a>
      </div>
      <div class="footer setup-footer" v-show="needSetup">
        <ShieldCheck :size="14" /> 数据将持久化存储在 local.db
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page { width: 100vw; height: 100vh; background-color: var(--color-bg-page); display: flex; align-items: center; justify-content: center; background-image: radial-gradient(var(--color-border) 1px, transparent 0); background-size: 32px 32px; }
.login-card { width: 400px; padding: 48px; background: white; border-radius: var(--radius-xl); box-shadow: var(--shadow-md); border: 1px solid var(--color-border); display: flex; flex-direction: column; }
.header { text-align: center; margin-bottom: 40px; }
.logo-circle { width: 48px; height: 48px; background: var(--color-primary); color: white; border-radius: 12px; margin: 0 auto 24px; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 700; }
.header h1 { font-size: 24px; margin-bottom: 8px; font-weight: var(--font-weight-bold); }
.header p { color: var(--color-text-secondary); font-size: 13px; font-weight: var(--font-weight-light); line-height: 1.5; }
.form { display: flex; flex-direction: column; gap: 20px; }
.form-item label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 8px; color: var(--color-text-secondary); }
.label-row { display: flex; justify-content: space-between; align-items: center; }
.forgot-link { color: var(--color-primary); font-size: 12px; text-decoration: none; }
.input-container { position: relative; width: 100%; }
.icon { position: absolute; left: 12px; top: 50%; translate: 0 -50%; color: var(--color-text-disabled); }
.input-container input { width: 100%; height: 42px; padding: 0 12px 0 38px; border: 1px solid var(--color-border); border-radius: var(--radius-md); outline: none; transition: var(--transition); font-size: 14px; }
.input-container input:focus { border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--color-primary-light); }
.divider { margin: 32px 0; display: flex; align-items: center; color: var(--color-text-disabled); font-size: 12px; }
.divider::before, .divider::after { content: ""; flex: 1; height: 1px; background: var(--color-border); }
.divider span { padding: 0 16px; }
.social-login { display: flex; justify-content: center; gap: 16px; }
.social-btn { width: 44px; height: 44px; border-radius: var(--radius-md); border: 1px solid var(--color-border); background: white; cursor: pointer; transition: var(--transition); color: var(--color-text-primary); display: flex; align-items: center; justify-content: center; }
.social-btn:hover { border-color: var(--color-primary); color: var(--color-primary); background: var(--color-primary-light); }
.social-btn.wechat:hover { color: #07C160; background: #E1F7EA; border-color: #07C160; }
.footer { margin-top: 40px; text-align: center; font-size: 13px; color: var(--color-text-secondary); }
.footer a { color: var(--color-primary); text-decoration: none; font-weight: 500; }
.setup-footer { display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 11px; opacity: 0.8; }
</style>

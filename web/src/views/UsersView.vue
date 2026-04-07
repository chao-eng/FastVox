<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { UserPlus, User, Trash2, Mail, Shield, CheckCircle, X } from 'lucide-vue-next';
import BaseButton from '../components/ui/BaseButton.vue';
import client from '../api/client';

const users = ref<any[]>([]);
const showModal = ref(false);
const isSubmitting = ref(false);

const form = ref({
  email: '',
  password: '',
  nickname: '',
  is_superuser: false,
});

const fetchUsers = async () => {
  try {
    const data: any = await client.get('/admin/users/');
    users.value = data;
  } catch (err) {
    console.error('Failed to fetch users:', err);
  }
};

const handleCreateUser = async () => {
  if (!form.value.email || !form.value.password) {
    alert('请输入邮箱和密码');
    return;
  }
  isSubmitting.value = true;
  try {
    await client.post('/admin/users/', form.value);
    showModal.value = false;
    form.value = { email: '', password: '', nickname: '', is_superuser: false };
    fetchUsers();
  } catch (err: any) {
    alert(err.response?.data?.detail || '创建用户失败');
  } finally {
    isSubmitting.value = false;
  }
};

const deleteUser = async (id: string) => {
  if (!confirm('确定要删除该用户吗？')) return;
  try {
    await client.delete(`/admin/users/${id}`);
    fetchUsers();
  } catch (err: any) {
    alert(err.response?.data?.detail || '删除失败');
  }
};

onMounted(fetchUsers);
</script>

<template>
  <div class="user-management">
    <div class="header-action">
      <div class="title-group">
        <h2>用户管理</h2>
        <p>创建、查看和管理系统内的用户信息</p>
      </div>
      <BaseButton type="primary" size="md" @click="showModal = true">
        <UserPlus :size="16" /> 新增用户
      </BaseButton>
    </div>

    <div class="user-list">
      <div v-for="user in users" :key="user.id" class="user-card">
        <div class="user-avatar">
          <div class="avatar-circle">
            {{ (user.nickname || user.email).charAt(0).toUpperCase() }}
          </div>
        </div>
        <div class="user-details">
          <div class="name-status">
            <h4>{{ user.nickname || '未设置昵称' }}</h4>
            <span v-if="user.is_superuser" class="badge admin">管理员</span>
            <span v-else class="badge">普通用户</span>
          </div>
          <div class="email"><Mail :size="14" /> {{ user.email }}</div>
          <div class="meta">ID: {{ user.id.substring(0, 8) }}...</div>
        </div>
        <div class="actions">
          <BaseButton type="text" size="sm" class="delete-btn" @click="deleteUser(user.id)">
            <Trash2 :size="16" />
          </BaseButton>
        </div>
      </div>
    </div>

    <!-- 创建用户弹窗 -->
    <Teleport to="body">
      <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
        <div class="modal">
          <div class="modal-header">
            <h3>新增用户档案</h3>
            <button class="close-btn" @click="showModal = false"><X :size="20" /></button>
          </div>
          <form @submit.prevent="handleCreateUser">
            <div class="modal-body">
              <div class="form-item">
                <label>电子邮箱 (登录账号)</label>
                <input v-model="form.email" type="email" placeholder="user@example.com" class="input" autocomplete="username" />
              </div>
              <div class="form-item">
                <label>登录密码</label>
                <input v-model="form.password" type="password" placeholder="请输入 8 位以上密码" class="input" autocomplete="new-password" />
              </div>
              <div class="form-item">
                <label>显示昵称</label>
                <input v-model="form.nickname" type="text" placeholder="例如：张三" class="input" autocomplete="nickname" />
              </div>
              <div class="form-item checkbox">
                <label>
                  <input type="checkbox" v-model="form.is_superuser" />
                  设为超级管理员 (具有系统最高权限)
                </label>
              </div>
            </div>
            <div class="modal-footer">
              <BaseButton @click="showModal = false" type="secondary">取消</BaseButton>
              <BaseButton type="primary" :loading="isSubmitting">立即创建</BaseButton>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.user-management { width: 100%; }
.header-action { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; }
.title-group h2 { font-size: 24px; margin-bottom: 8px; }
.title-group p { font-size: 14px; color: var(--color-text-secondary); font-weight: var(--font-weight-light); }

.user-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }

.user-card {
  background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg);
  padding: 16px 20px; display: flex; align-items: center; gap: 16px; transition: var(--transition);
}
.user-card:hover { border-color: var(--color-primary); box-shadow: var(--shadow-sm); }

.avatar-circle {
  width: 48px; height: 48px; background: var(--color-primary-light); color: var(--color-primary);
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 18px;
}

.user-details { flex: 1; }
.name-status { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.name-status h4 { font-size: 16px; font-weight: 600; margin: 0; }

.badge {
  font-size: 11px; padding: 2px 8px; border-radius: 4px;
  background: var(--color-bg-page); color: var(--color-text-secondary); font-weight: 500;
}
.badge.admin { background: #E8FFFB; color: #00B42A; }

.email { font-size: 13px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 4px; margin-bottom: 4px; }
.meta { font-size: 12px; color: var(--color-text-disabled); }

.actions { display: flex; gap: 8px; }
.delete-btn { color: var(--color-text-disabled); }
.delete-btn:hover { color: var(--color-danger); }

/* Modal Styles - Reuse from VoiceView if possible, or define here if specific */
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); backdrop-filter: blur(4px); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal { background: var(--color-bg-card); width: 100%; max-width: 480px; border-radius: var(--radius-xl); box-shadow: var(--shadow-md); overflow: hidden; }
.modal-header { padding: 20px 24px; border-bottom: 1px solid var(--color-border); display: flex; justify-content: space-between; align-items: center; }
.close-btn { background: transparent; border: none; color: var(--color-text-disabled); cursor: pointer; }

.modal-body { padding: 24px; }
.form-item { margin-bottom: 20px; }
.form-item label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 8px; color: var(--color-text-secondary); }
.input { width: 100%; border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 10px 12px; outline: none; transition: var(--transition); }
.input:focus { border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--color-primary-light); }

.checkbox label { display: flex; align-items: center; gap: 8px; font-weight: 400; font-size: 13px; cursor: pointer; }
.checkbox input { width: 16px; height: 16px; }

.modal-footer { padding: 16px 24px; background: var(--color-bg-page); display: flex; justify-content: flex-end; gap: 12px; }
</style>

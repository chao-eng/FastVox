<script setup lang="ts">
import { ref } from 'vue';
import { Plus, Mic, Trash2, Calendar, FileText, UploadCloud, X } from 'lucide-vue-next';
import BaseButton from '../components/ui/BaseButton.vue';

const showModal = ref(false);
const voices = ref([
  { id: '1', name: '温柔女声 A', text: '这是一个测试句子。', duration: '5.2s', created: '2024-04-05' },
  { id: '2', name: '沉稳男声 B', text: '欢迎使用 FastVox 系统。', duration: '8.4s', created: '2024-04-04' },
]);

const handleUpload = () => {
  // TODO: 后端 API 调用
  showModal.value = false;
};
</script>

<template>
  <div class="voices">
    <div class="header-action">
      <div class="title-group">
        <h2>声纹管理</h2>
        <p>上传 3s-30s 参考音频以执行 In-context Learning 合成</p>
      </div>
      <BaseButton type="primary" size="md" @click="showModal = true">
        <Plus :size="16" /> 新增声纹
      </BaseButton>
    </div>

    <div class="voice-grid">
      <div v-for="v in voices" :key="v.id" class="voice-card">
        <div class="card-top">
          <div class="icon-box"><Mic :size="20" stroke-width="1.5" /></div>
          <div class="voice-info">
            <h4>{{ v.name }}</h4>
            <span class="duration">{{ v.duration }}</span>
          </div>
        </div>
        
        <div class="card-body">
          <div class="text-hint">参考文本:</div>
          <p class="prompt-text">{{ v.text }}</p>
        </div>

        <div class="card-footer">
          <div class="meta"><Calendar :size="14" /> {{ v.created }}</div>
          <BaseButton type="text" size="sm" class="delete-btn">
            <Trash2 :size="14" />
          </BaseButton>
        </div>
      </div>

      <div class="add-card" @click="showModal = true">
        <UploadCloud :size="32" stroke-width="1" />
        <p>点此上传新款声纹</p>
      </div>
    </div>

    <!-- 极简上传弹窗 -->
    <Teleport to="body">
      <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
        <div class="modal">
          <div class="modal-header">
            <h3>上传声纹档案</h3>
            <button class="close-btn" @click="showModal = false"><X :size="20" /></button>
          </div>
          <div class="modal-body">
            <div class="form-item">
              <label>声纹名称</label>
              <input type="text" placeholder="例如：温柔青年音" class="input" />
            </div>
            <div class="form-item">
              <label>参考文本 (与录音内容一致)</label>
              <textarea placeholder="请输入参考音频对应的文本内容..." class="textarea"></textarea>
            </div>
            <div class="drop-zone">
              <UploadCloud :size="48" stroke-width="1" />
              <p>点击或拖拽 WAV/MP3 文件至此处</p>
              <span class="limit">建议时长 3s-15s, 文件不超过 10MB</span>
            </div>
          </div>
          <div class="modal-footer">
            <BaseButton @click="showModal = false">取消</BaseButton>
            <BaseButton type="primary" @click="handleUpload">开始提取</BaseButton>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.voices { width: 100%; }
.header-action { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; }
.title-group h2 { font-size: 24px; margin-bottom: 8px; }
.title-group p { font-size: 14px; color: var(--color-text-secondary); font-weight: var(--font-weight-light); }

.voice-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px; }

.voice-card {
  background: white; border: 1px solid var(--color-border); border-radius: var(--radius-lg);
  padding: 20px; transition: var(--transition); display: flex; flex-direction: column;
}

.voice-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); border-color: var(--color-primary); }

.card-top { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.icon-box { 
  width: 40px; height: 40px; background: var(--color-primary-light); 
  color: var(--color-primary); border-radius: 10px; display: flex; 
  align-items: center; justify-content: center;
}
.voice-info h4 { font-weight: var(--font-weight-semibold); font-size: 16px; margin-bottom: 2px; }
.duration { font-size: 12px; color: var(--color-text-secondary); font-weight: var(--font-weight-light); }

.text-hint { font-size: 11px; color: var(--color-text-disabled); font-weight: 600; text-transform: uppercase; margin-bottom: 4px; }
.prompt-text { font-size: 13px; line-height: 1.5; height: 40px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; color: var(--color-text-secondary); }

.card-footer { margin-top: auto; padding-top: 16px; border-top: 1px dashed var(--color-border); display: flex; justify-content: space-between; align-items: center; }
.meta { font-size: 12px; color: var(--color-text-disabled); display: flex; align-items: center; gap: 4px; }
.delete-btn { color: var(--color-text-disabled); }
.delete-btn:hover { color: var(--color-danger); }

.add-card {
  border: 2px dashed var(--color-border); border-radius: var(--radius-lg);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--color-text-disabled); cursor: pointer; transition: var(--transition); min-height: 180px;
}
.add-card:hover { border-color: var(--color-primary); color: var(--color-primary); background: var(--color-primary-light); }
.add-card p { margin-top: 12px; font-size: 14px; font-weight: 500; }

/* Modal Styles */
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); backdrop-filter: blur(4px); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal { background: white; width: 100%; max-width: 500px; border-radius: var(--radius-xl); box-shadow: var(--shadow-md); overflow: hidden; }
.modal-header { padding: 20px 24px; border-bottom: 1px solid var(--color-border); display: flex; justify-content: space-between; align-items: center; }
.modal-header h3 { font-size: 18px; }
.close-btn { background: transparent; border: none; color: var(--color-text-disabled); cursor: pointer; }

.modal-body { padding: 24px; }
.form-item { margin-bottom: 20px; }
.form-item label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 8px; color: var(--color-text-secondary); }
.input, .textarea { width: 100%; border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 10px 12px; outline: none; transition: var(--transition); }
.input:focus, .textarea:focus { border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--color-primary-light); }
.textarea { height: 80px; resize: none; line-height: 1.6; }

.drop-zone { 
  border: 2px dashed var(--color-border); border-radius: var(--radius-lg);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 32px; color: var(--color-text-disabled); cursor: pointer;
}
.drop-zone:hover { background: var(--color-bg-page); color: var(--color-primary); border-color: var(--color-primary); }
.drop-zone p { margin: 12px 0 4px; font-weight: 500; }
.limit { font-size: 11px; }

.modal-footer { padding: 16px 24px; background: var(--color-bg-page); display: flex; justify-content: flex-end; gap: 12px; }
</style>

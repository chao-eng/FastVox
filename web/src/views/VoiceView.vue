<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Plus, Mic, Trash2, Calendar, FileText, UploadCloud, X, Play, Pause } from 'lucide-vue-next';
import BaseButton from '../components/ui/BaseButton.vue';
import client from '../api/client';

const fileInput = ref<HTMLInputElement | null>(null);
const showModal = ref(false);
const voices = ref<any[]>([]);
const isUploading = ref(false);
const isDragOver = ref(false);

const audio = new Audio();
const currentlyPlaying = ref<string | null>(null);
const isLoadingAudio = ref<string | null>(null);

// 表单数据
const form = ref({
  name: '',
  prompt_text: '',
  file: null as File | null,
});

const fetchVoices = async () => {
  try {
    const data: any = await client.get('/voice/list');
    voices.value = data;
  } catch (err) { console.error('Failed to fetch voices:', err); }
};

const handleFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    form.value.file = target.files[0];
  }
};

const triggerFileInput = () => {
  fileInput.value?.click();
};

const handleDragOver = (e: DragEvent) => {
  e.preventDefault();
  isDragOver.value = true;
};

const handleDragLeave = () => {
  isDragOver.value = false;
};

const handleDrop = (e: DragEvent) => {
  e.preventDefault();
  isDragOver.value = false;
  if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
    form.value.file = e.dataTransfer.files[0];
  }
};

const handleUpload = async () => {
  if (!form.value.file || !form.value.name) {
    alert('请填写名称并选择音频文件');
    return;
  }
  isUploading.value = true;
  
  const formData = new FormData();
  formData.append('file', form.value.file);
  formData.append('name', form.value.name);
  formData.append('prompt_text', form.value.prompt_text);

  try {
    await client.post('/voice/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    showModal.value = false;
    // 重置表单
    form.value = { name: '', prompt_text: '', file: null };
    fetchVoices();
  } catch (err) { 
    alert('上传失败，请检查文件格式及网络'); 
  } finally { 
    isUploading.value = false; 
  }
};

const deleteVoice = async (id: string) => {
  if (!confirm('确定删除该声纹吗？')) return;
  try {
    await client.delete(`/voice/${id}`);
    fetchVoices();
  } catch (err) {
    alert('删除失败');
  }
};

const playVoice = async (id: string) => {
  if (currentlyPlaying.value === id) {
    audio.pause();
    currentlyPlaying.value = null;
    return;
  }

  isLoadingAudio.value = id;
  try {
    // 使用 axios client 以便带上 Auth Token
    const blob: any = await client.get(`/voice/${id}/audio`, {
      responseType: 'blob'
    });
    
    const blobUrl = URL.createObjectURL(blob);
    audio.src = blobUrl;
    await audio.play();
    currentlyPlaying.value = id;
    
    audio.onended = () => {
      currentlyPlaying.value = null;
      URL.revokeObjectURL(blobUrl);
    };
    
    // 如果中途切换了音频，也需要释放
    audio.onplay = () => {
      isLoadingAudio.value = null;
    };

  } catch (err) {
    console.error('Playback error:', err);
    alert('播放失败');
  } finally {
    isLoadingAudio.value = null;
  }
};

onMounted(fetchVoices);
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
            <span class="duration">{{ v.duration_sec?.toFixed(1) }}s</span>
          </div>
          <button 
            class="play-preview-btn" 
            :class="{ playing: currentlyPlaying === v.id }"
            @click="playVoice(v.id)"
            :disabled="isLoadingAudio === v.id"
          >
            <component :is="currentlyPlaying === v.id ? Pause : Play" :size="16" />
          </button>
        </div>
        
        <div class="card-body">
          <div class="text-hint">注册日期:</div>
          <p class="meta">{{ new Date(v.created_at).toLocaleDateString() }}</p>
        </div>

        <div class="card-footer">
          <div class="meta"><Calendar :size="14" /> {{ new Date(v.created_at).toLocaleTimeString() }}</div>
          <BaseButton type="text" size="sm" class="delete-btn" @click="deleteVoice(v.id)">
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
              <input v-model="form.name" type="text" placeholder="例如：温柔青年音" class="input" />
            </div>
            <div class="form-item">
              <label>参考文本 (与录音内容一致)</label>
              <textarea v-model="form.prompt_text" placeholder="请输入参考音频对应的文本内容..." class="textarea"></textarea>
            </div>

            <!-- 隐藏的文件输入框 -->
            <input 
              ref="fileInput"
              type="file" 
              style="display: none" 
              accept=".wav,.mp3" 
              @change="handleFileChange" 
            />

            <div 
              class="drop-zone" 
              :class="{ active: isDragOver || form.file }"
              @click="triggerFileInput"
              @dragover="handleDragOver"
              @dragleave="handleDragLeave"
              @drop="handleDrop"
            >
              <UploadCloud v-if="!form.file" :size="48" stroke-width="1" />
              <FileText v-else :size="48" stroke-width="1" class="file-icon" />
              
              <p v-if="!form.file">点击或拖拽 WAV/MP3 文件至此处</p>
              <p v-else class="file-name">{{ form.file.name }}</p>
              
              <span class="limit">建议时长 3s-15s, 文件不超过 10MB</span>
            </div>
          </div>
          <div class="modal-footer">
            <BaseButton @click="showModal = false">取消</BaseButton>
            <BaseButton type="primary" :loading="isUploading" @click="handleUpload">开始提取</BaseButton>
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
  background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg);
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

.play-preview-btn {
  margin-left: auto; width: 32px; height: 32px; 
  border-radius: 50%; border: none; background: var(--color-bg-page);
  color: var(--color-primary); cursor: pointer; display: flex;
  align-items: center; justify-content: center; transition: var(--transition);
}
.play-preview-btn:hover { background: var(--color-primary-light); transform: scale(1.1); }
.play-preview-btn.playing { background: var(--color-primary); color: white; animation: pulse 2s infinite; }

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(79, 70, 229, 0); }
  100% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0); }
}

.add-card {
  border: 2px dashed var(--color-border); border-radius: var(--radius-lg);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--color-text-disabled); cursor: pointer; transition: var(--transition); min-height: 180px;
}
.add-card:hover { border-color: var(--color-primary); color: var(--color-primary); background: var(--color-primary-light); }
.add-card p { margin-top: 12px; font-size: 14px; font-weight: 500; }

/* Modal Styles */
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); backdrop-filter: blur(4px); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal { background: var(--color-bg-card); width: 100%; max-width: 500px; border-radius: var(--radius-xl); box-shadow: var(--shadow-md); overflow: hidden; }
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
.drop-zone:hover, .drop-zone.active { background: var(--color-bg-page); color: var(--color-primary); border-color: var(--color-primary); }
.drop-zone p { margin: 12px 0 4px; font-weight: 500; }
.file-name { color: var(--color-primary); font-weight: 600; }
.limit { font-size: 11px; }

.modal-footer { padding: 16px 24px; background: var(--color-bg-page); display: flex; justify-content: flex-end; gap: 12px; }
</style>

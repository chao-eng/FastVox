<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { Play, Download, Mic, Trash2, Send } from 'lucide-vue-next';
import BaseButton from '../components/ui/BaseButton.vue';
import client from '../api/client';

const text = ref('');
const voiceId = ref('');
const speed = ref(1.0);
const isSynthesizing = ref(false);
const audioUrl = ref<string | null>(null);
const voices = ref<any[]>([]);

const maxTextLength = 500;
const textLength = computed(() => text.value.length);
const isTextOverLimit = computed(() => textLength.value > maxTextLength);

const fetchVoices = async () => {
  voices.value = await client.get('/voice/list');
  if (voices.value.length > 0) voiceId.value = voices.value[0].id;
};

const handleSynthesize = () => {
  if (!text.value || !voiceId.value) return;
  isSynthesizing.value = true;
  audioUrl.value = null;

  // 获取后端端口，建立 WebSocket 连接
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws?token=${localStorage.getItem('fastvox_token')}`;
  
  const socket = new WebSocket(wsUrl);
  socket.binaryType = 'arraybuffer';
  const audioChunks: Uint8Array[] = [];

  socket.onopen = () => {
    socket.send(JSON.stringify({
      text: text.value,
      voice_id: voiceId.value,
      speed: speed.value
    }));
  };

  socket.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      if (event.data.byteLength === 0) {
        // 结束帧
        socket.close();
      } else {
        audioChunks.push(new Uint8Array(event.data));
      }
    }
  };

  socket.onclose = () => {
    isSynthesizing.value = false;
    if (audioChunks.length > 0) {
      const blob = new Blob(audioChunks as any, { type: 'audio/ogg' });
      audioUrl.value = URL.createObjectURL(blob);
    }
  };

  socket.onerror = () => {
    isSynthesizing.value = false;
    alert('WebSocket 合成连接失败');
  };
};

const downloadAudio = () => {
  if (!audioUrl.value) return;
  const link = document.createElement('a');
  link.href = audioUrl.value;
  link.download = `fastvox_${Date.now()}.ogg`;
  link.click();
};

onMounted(fetchVoices);
</script>

<template>
  <div class="synthesis">
    <div class="container">
      <div class="left-panel">
        <div class="card editor-card">
          <div class="card-header">
            <h3>文本输入</h3>
            <span :class="['count', { over: isTextOverLimit }]">
              {{ textLength }} / {{ maxTextLength }}
            </span>
          </div>
          <textarea v-model="text" placeholder="请输入您想要合成的文本内容..." class="textarea"></textarea>
          <div class="toolbar">
            <BaseButton type="text" size="sm" @click="text = ''">
              <Trash2 :size="14" /> 清空文本
            </BaseButton>
            <BaseButton type="primary" size="lg" :loading="isSynthesizing" :disabled="!text || isTextOverLimit" @click="handleSynthesize">
              <Send :size="18" /> 开始合成
            </BaseButton>
          </div>
        </div>

        <div class="card settings-card">
          <h3>推理参数</h3>
          <div class="field">
            <label>选择声纹</label>
            <select v-model="voiceId" class="select">
              <option v-for="v in voices" :key="v.id" :value="v.id">{{ v.name }}</option>
            </select>
          </div>
          <div class="field">
            <div class="label-row">
              <label>合成语速</label>
              <span>{{ speed.toFixed(2) }}x</span>
            </div>
            <input type="range" v-model.number="speed" min="0.5" max="2.0" step="0.1" class="slider" />
          </div>
        </div>
      </div>

      <div class="right-panel">
        <div class="card player-card">
          <h3>音频播放器</h3>
          <div v-if="!audioUrl && !isSynthesizing" class="placeholder">
            <Mic :size="48" color="#E5E6EB" />
            <p>等待任务提交...</p>
          </div>
          
          <div v-if="isSynthesizing" class="skeleton">
            <div class="skeleton-wave"></div>
            <p>正在执行流式推理...</p>
          </div>

          <div v-if="audioUrl && !isSynthesizing" class="player">
            <audio controls :src="audioUrl" style="width: 100%; margin-bottom: 20px;"></audio>
            <div class="player-actions">
              <BaseButton type="secondary" size="md" @click="downloadAudio">
                <Download :size="18" /> 保存录音
              </BaseButton>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.synthesis { width: 100%; max-width: 1200px; margin: 0 auto; }
.container { display: grid; grid-template-columns: 1.5fr 1fr; gap: 24px; }
.card { background: white; border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 24px; box-shadow: var(--shadow-sm); margin-bottom: 24px; }
.card h3 { font-size: 16px; margin-bottom: 16px; color: var(--color-text-primary); }
.editor-card { display: flex; flex-direction: column; min-height: 400px; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.count { font-size: 12px; color: var(--color-text-secondary); font-weight: var(--font-weight-light); }
.count.over { color: var(--color-danger); font-weight: bold; }
.textarea { flex: 1; border: none; background: transparent; resize: none; outline: none; font-size: 16px; line-height: 1.6; color: var(--color-text-primary); min-height: 200px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; padding-top: 16px; border-top: 1px solid var(--color-border); }
.settings-card .field { margin-bottom: 20px; }
.settings-card label { display: block; font-size: 13px; color: var(--color-text-secondary); margin-bottom: 8px; font-weight: 500; }
.label-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.select { width: 100%; height: 36px; border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 0 12px; outline: none; }
.slider { width: 100%; -webkit-appearance: none; height: 4px; background: var(--color-border); border-radius: 2px; }
.slider::-webkit-slider-thumb { -webkit-appearance: none; width: 16px; height: 16px; background: var(--color-primary); border-radius: 50%; cursor: pointer; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.1); }
.player-card { min-height: 240px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
.placeholder { color: var(--color-text-disabled); }
.placeholder p { margin-top: 12px; font-size: 14px; }
.skeleton { width: 100%; }
.skeleton-wave { height: 64px; background: var(--color-bg-page); border-radius: 8px; animation: pulse 1.5s infinite; margin-bottom: 12px; }
@keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 0.3; } 100% { opacity: 0.6; } }
.player { width: 100%; }
.player-actions { display: flex; gap: 12px; justify-content: center; align-items: center; }
</style>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { Play, Download, Mic, Trash2, Send } from 'lucide-vue-next';
import BaseButton from '../components/ui/BaseButton.vue';
import client from '../api/client';

const text = ref('');
const voiceId = ref('');
const speed = ref(1.0);
const isSynthesizing = ref(false);
const audioUrl = ref<string | null>(null);
const voices = ref<any[]>([]);

// 流式播放管理器
let mediaSource: MediaSource | null = null;
let sourceBuffer: SourceBuffer | null = null;
let audioChunkQueue: Uint8Array[] = [];

const maxTextLength = 500;
const textLength = computed(() => text.value.length);
const isTextOverLimit = computed(() => textLength.value > maxTextLength);

const fetchVoices = async () => {
  voices.value = await client.get('/voice/list');
  if (voices.value.length > 0) voiceId.value = voices.value[0].id;
};

const handleSynthesize = () => {
  if (!text.value || !voiceId.value) return;
  
  // 1. 初始化状态
  isSynthesizing.value = true;
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value);
  audioUrl.value = null;
  
  const audioChunks: Uint8Array[] = [];
  audioChunkQueue = [];

  // 2. 初始化 MediaSource (MSE) 实现边下边播
  mediaSource = new MediaSource();
  audioUrl.value = URL.createObjectURL(mediaSource);

  mediaSource.addEventListener('sourceopen', () => {
    if (!mediaSource) return;
    try {
      sourceBuffer = mediaSource.addSourceBuffer('audio/webm; codecs="opus"');
      sourceBuffer.addEventListener('updateend', () => {
        // 当 Buffer 更新完成后，处理队列中的剩余数据
        if (audioChunkQueue.length > 0 && sourceBuffer && !sourceBuffer.updating) {
          const nextChunk = audioChunkQueue.shift()!;
          sourceBuffer.appendBuffer(nextChunk.buffer as ArrayBuffer);
        }
      });
    } catch (e) {
      console.warn("MSE not supported for audio/ogg, falling back to Blob mode.", e);
    }
  });

  // 3. 建立 WebSocket 连接
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws?token=${localStorage.getItem('fastvox_token')}`;
  const socket = new WebSocket(wsUrl);
  socket.binaryType = 'arraybuffer';

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
        socket.close();
        return;
      }

      const chunk = new Uint8Array(event.data);
      audioChunks.push(chunk);

      // 将分片送入 MSE Buffer
      if (sourceBuffer && !sourceBuffer.updating && audioChunkQueue.length === 0) {
        sourceBuffer.appendBuffer(chunk.buffer as ArrayBuffer);
      } else {
        audioChunkQueue.push(chunk);
      }
    }
  };

  socket.onclose = () => {
    isSynthesizing.value = false;
    
    // 告知 MediaSource 数据已传完
    if (mediaSource && mediaSource.readyState === 'open') {
      // 延迟关闭，确保排队中的 Buffer 处理完
      setTimeout(() => {
        if (mediaSource && mediaSource.readyState === 'open') {
          mediaSource.endOfStream();
        }
      }, 500);
    }

    // 依然保留一个完整的 Blob 供后续“下载”使用
    if (audioChunks.length > 0) {
      const fullBlob = new Blob(audioChunks as any, { type: 'audio/webm' });
      // 只有在不支持 MSE 或者需要持久化 URL 时才替换
      // 这里我们为了保持进度条能正常 seek，合成完后将 URL 替换为完整 Blob
      if (audioUrl.value) URL.revokeObjectURL(audioUrl.value);
      audioUrl.value = URL.createObjectURL(fullBlob);
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
  link.download = `fastvox_${Date.now()}.webm`;
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
            <BaseButton type="primary" size="lg" :loading="isSynthesizing" :disabled="!text || !voiceId || isTextOverLimit" @click="handleSynthesize">
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
          
          <div v-if="audioUrl" class="player">
            <div v-if="isSynthesizing" class="streaming-indicator">
              <div class="dot-flashing"></div>
              <span>流式合成中，可即时播放...</span>
            </div>
            <audio controls :src="audioUrl" style="width: 100%; margin-bottom: 20px;"></audio>
            <div class="player-actions">
              <BaseButton type="secondary" size="md" :disabled="isSynthesizing" @click="downloadAudio">
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

.streaming-indicator { display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 12px; color: var(--color-primary); font-size: 13px; font-weight: 500; }
.dot-flashing { position: relative; width: 6px; height: 6px; border-radius: 5px; background-color: var(--color-primary); color: var(--color-primary); animation: dot-flashing 1s infinite linear alternate; animation-delay: 0.5s; }
.dot-flashing::before, .dot-flashing::after { content: ""; display: inline-block; position: absolute; top: 0; width: 6px; height: 6px; border-radius: 5px; background-color: var(--color-primary); color: var(--color-primary); animation: dot-flashing 1s infinite linear alternate; }
.dot-flashing::before { left: -10px; animation-delay: 0s; }
.dot-flashing::after { left: 10px; animation-delay: 1s; }
@keyframes dot-flashing { 0% { background-color: var(--color-primary); } 50%, 100% { background-color: #E1EAFF; } }
</style>

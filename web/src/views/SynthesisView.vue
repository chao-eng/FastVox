<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { Play, Download, Mic, Trash2, Send, Volume2 } from 'lucide-vue-next';
import BaseButton from '../components/ui/BaseButton.vue';
import client from '../api/client';

const text = ref('');
const voiceId = ref('');
const speed = ref(1.0);
const isSynthesizing = ref(false);
const hasReceivedData = ref(false);
const audioChunks = ref<Uint8Array[]>([]); // 修改：提升为响应式 ref 供模板使用
const audioUrl = ref<string | null>(null);
const voices = ref<any[]>([]);
const isSuperuser = ref(false);

// 流式播放管理器
let mediaSource: MediaSource | null = null;
let sourceBuffer: SourceBuffer | null = null;
let audioChunkQueue: Uint8Array[] = [];

const maxTextLength = 500;
const textLength = computed(() => text.value.length);
const isTextOverLimit = computed(() => textLength.value > maxTextLength);
const currentVoice = computed(() => voices.value.find(v => v.id === voiceId.value));
const isPreviewPlaying = ref(false);
let previewAudio: HTMLAudioElement | null = null;

const fetchVoices = async () => {
  voices.value = await client.get('/voice/list');
  if (voices.value.length > 0 && !voiceId.value) voiceId.value = voices.value[0].id;
  
  try {
    const user: any = await client.get('/users/me');
    isSuperuser.value = !!user.is_superuser;
  } catch (err) { console.error('Failed to fetch user info:', err); }
};

const toggleVoicePreview = () => {
  if (isPreviewPlaying.value) {
    previewAudio?.pause();
    isPreviewPlaying.value = false;
    return;
  }

  if (!voiceId.value) return;

  const url = `/api/voice/${voiceId.value}/audio?token=${localStorage.getItem('fastvox_token')}`;
  previewAudio = new Audio(url);
  previewAudio.play();
  isPreviewPlaying.value = true;
  previewAudio.onended = () => {
    isPreviewPlaying.value = false;
  };
};

const totalDurationMs = ref(0); // 实时计算合成的总时长

// 将毫秒转换为 00:00.0s 格式
const formatDuration = (ms: number) => {
  const seconds = ms / 1000;
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(1);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(4, '0')}s`;
};

const handleSynthesize = () => {
  if (!text.value || !voiceId.value) return;
  
  // 1. 初始化状态
  isSynthesizing.value = true;
  hasReceivedData.value = false;
  totalDurationMs.value = 0; // 重置时长统计
  audioChunks.value = []; // 重置分片统计
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value);
  audioUrl.value = null;
  
  audioChunkQueue = [];

  // 2. 初始化 MediaSource (MSE) 实现边下边播
  mediaSource = new MediaSource();
  audioUrl.value = URL.createObjectURL(mediaSource);

  mediaSource.addEventListener('sourceopen', () => {
    if (!mediaSource) return;
    try {
      sourceBuffer = mediaSource.addSourceBuffer('audio/webm; codecs="opus"');
      
      // 关键修复：如果在 Buffer 就绪前已经有分片到达了队列，立刻喂入第一个分片触发更新循环
      if (audioChunkQueue.length > 0 && sourceBuffer && !sourceBuffer.updating) {
        const firstChunk = audioChunkQueue.shift()!;
        sourceBuffer.appendBuffer(firstChunk.buffer as ArrayBuffer);
      }

      sourceBuffer.addEventListener('updateend', () => {
        // 当 Buffer 更新完成后，自动处理队列中的剩余数据
        if (audioChunkQueue.length > 0 && sourceBuffer && !sourceBuffer.updating) {
          const nextChunk = audioChunkQueue.shift()!;
          sourceBuffer.appendBuffer(nextChunk.buffer as ArrayBuffer);
        }
      });

      sourceBuffer.addEventListener('error', (e) => {
        console.error("SourceBuffer error:", e);
      });
    } catch (e) {
      console.warn("MSE not supported for audio/webm, falling back to Blob mode.", e);
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
    // 监听：或者是二进制音频流
    if (event.data instanceof ArrayBuffer) {
      if (event.data.byteLength === 0) {
        socket.close();
        return;
      }

      const chunk = new Uint8Array(event.data);
      audioChunks.value.push(chunk);
      hasReceivedData.value = true; // 标记已开始接收数据

      // 将分片送入 MSE Buffer
      if (sourceBuffer && !sourceBuffer.updating && audioChunkQueue.length === 0) {
        sourceBuffer.appendBuffer(chunk.buffer as ArrayBuffer);
      } else {
        audioChunkQueue.push(chunk);
      }
    } 
    // 或者是非二进制消息 (元数据)
    else if (typeof event.data === 'string') {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'metadata' && msg.segment_duration_ms) {
          totalDurationMs.value += msg.segment_duration_ms;
        }
      } catch (e) {
        // 忽略非 JSON
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
    if (audioChunks.value.length > 0) {
      const fullBlob = new Blob(audioChunks.value as any, { type: 'audio/webm' });
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
            <div class="label-row">
              <label>选择声纹</label>
              <BaseButton 
                v-if="voiceId" 
                type="text" 
                size="sm" 
                :class="['preview-btn', { playing: isPreviewPlaying }]" 
                @click="toggleVoicePreview"
              >
                <Volume2 :size="14" /> {{ isPreviewPlaying ? '停止试听' : '试听原声' }}
              </BaseButton>
            </div>
            <select v-model="voiceId" class="select">
              <option v-for="v in voices" :key="v.id" :value="v.id">
                {{ v.name }}{{ isSuperuser && v.is_public && !v.is_owner ? ' [公开]' : '' }}
              </option>
            </select>
            <div v-if="currentVoice" class="voice-hint">
              <strong>参考文本：</strong>{{ currentVoice.prompt_text }}
            </div>
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
          
          <!-- 状态 1: 推理已开始，但还未收到第一个片段 -->
          <div v-if="isSynthesizing && !hasReceivedData" class="status-container preparing">
            <div class="loader"></div>
            <p>正在初始化引擎并推理首个片段...</p>
          </div>

          <!-- 状态 2: 已有音频数据，但正在流式持续生成 -->
          <div v-if="isSynthesizing && hasReceivedData && audioUrl" class="player">
            <div class="streaming-indicator">
              <div class="pulse-bar"></div>
              <span>流式合成中 · 累计生成时长 {{ formatDuration(totalDurationMs) }} ({{ audioChunks.length }} 段)</span>
            </div>
            <audio controls autoplay :src="audioUrl" style="width: 100%; margin-bottom: 20px;"></audio>
            <div class="player-actions">
              <BaseButton type="secondary" size="md" disabled>
                <Download :size="18" /> 合成中...
              </BaseButton>
            </div>
          </div>

          <!-- 状态 3: 合成全部结束 -->
          <div v-if="!isSynthesizing && audioUrl" class="player">
            <div class="complete-indicator">
              <div class="check-icon">✓</div>
              <span>文本合成已全部完成 · 总时长 {{ formatDuration(totalDurationMs) }}</span>
            </div>
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
.card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 24px; box-shadow: var(--shadow-sm); margin-bottom: 24px; }
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
.select { width: 100%; height: 36px; border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 0 12px; outline: none; background: var(--color-bg-card); color: var(--color-text-primary); }
.voice-hint { margin-top: 8px; font-size: 12px; color: var(--color-text-secondary); line-height: 1.4; padding: 8px; background: var(--color-bg-page); border-radius: 4px; border-left: 3px solid var(--color-primary); }
.voice-hint strong { color: var(--color-text-primary); margin-right: 4px; }
.preview-btn { padding: 0; height: auto; font-size: 12px; }
.preview-btn.playing { color: var(--color-primary); font-weight: 600; }

.slider { width: 100%; -webkit-appearance: none; appearance: none; height: 4px; background: var(--color-border); border-radius: 2px; }
.slider::-webkit-slider-thumb { -webkit-appearance: none; width: 16px; height: 16px; background: var(--color-primary); border-radius: 50%; cursor: pointer; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.1); }
.player-card { min-height: 240px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
.placeholder { color: var(--color-text-disabled); }
.placeholder p { margin-top: 12px; font-size: 14px; }
.skeleton { width: 100%; }
.skeleton-wave { height: 64px; background: var(--color-bg-page); border-radius: 8px; animation: pulse 1.5s infinite; margin-bottom: 12px; }
@keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 0.3; } 100% { opacity: 0.6; } }
.player { width: 100%; }
.player-actions { display: flex; gap: 12px; justify-content: center; align-items: center; }

.status-container { display: flex; flex-direction: column; align-items: center; gap: 16px; }
.status-container p { font-size: 14px; color: var(--color-primary); font-weight: 500; }

/* 转圈动画 */
.loader { border: 3px solid #f3f3f3; border-top: 3px solid var(--color-primary); border-radius: 50%; width: 24px; height: 24px; animation: spin 1s linear infinite; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

.streaming-indicator { display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 12px; color: var(--color-primary); font-size: 13px; font-weight: 500; }
.pulse-bar { width: 12px; height: 12px; background: var(--color-primary); border-radius: 2px; animation: pulse 1.2s infinite; }
@keyframes pulse { 0% { transform: scale(0.9); opacity: 1; } 50% { transform: scale(1.1); opacity: 0.6; } 100% { transform: scale(0.9); opacity: 1; } }

.complete-indicator { display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 12px; color: var(--color-success); font-size: 13px; font-weight: 600; }
.check-icon { width: 18px; height: 18px; background: var(--color-success); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; }

</style>

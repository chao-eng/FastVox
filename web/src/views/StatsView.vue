<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { BarChart, Clock, Database, TrendingUp, Activity } from 'lucide-vue-next';
import client from '../api/client';

// 动态统计数据
const stats = ref([
  { name: '累计合成字数', value: '0', change: '+0%', icon: Database },
  { name: '平均推理时延', value: '0.00s', change: '+0%', icon: Clock },
  { name: '服务成功率', icon: Activity },
  { name: '今日实时请求', value: '0', change: '+0%', icon: TrendingUp },
]);

const throughput = ref<number[]>([]);

const iconMap: any = { Database, Clock, Activity, TrendingUp };

onMounted(async () => {
  try {
    const summary: any = await client.get('/stats/summary');
    stats.value = (summary as any).stats.map((s: any) => ({
      ...s,
      icon: iconMap[s.icon] || BarChart
    }));

    const tp: any = await client.get('/stats/throughput');
    throughput.value = (tp as any).data;
  } catch (err) {
    console.error('Failed to fetch stats:', err);
  }
});
</script>

<template>
  <div class="stats">
    <div class="stat-grid">
      <div v-for="s in stats" :key="s.name" class="stat-card">
        <div class="stat-top">
          <div class="icon-circle"><component :is="s.icon" :size="20" /></div>
          <span class="change">{{ s.change }}</span>
        </div>
        <div class="stat-main">
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-name">{{ s.name }}</div>
        </div>
      </div>
    </div>

    <!-- 吞吐量图表 -->
    <div class="charts-row">
      <div class="chart-card">
        <h3>每分钟实时推理吞吐量 (Requests/min)</h3>
        <div class="chart-container">
          <!-- Y 轴单位 -->
          <div class="y-axis">
            <span>{{ Math.max(...throughput, 5) }}</span>
            <span>{{ Math.floor(Math.max(...throughput, 5) / 2) }}</span>
            <span>0</span>
          </div>
          
          <div class="chart-main">
            <div class="chart-box">
              <div class="mock-bars">
                <div 
                  v-for="(val, idx) in throughput" 
                  :key="idx" 
                  class="bar" 
                  :style="{ height: (val / Math.max(...throughput, 1) * 100) + '%' }"
                  :title="`${val} reqs`"
                ></div>
              </div>
            </div>
            <!-- X 轴单位 -->
            <div class="x-axis">
              <span>20min 前</span>
              <span>10min 前</span>
              <span>现在</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats { width: 100%; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 24px; margin-bottom: 32px; }

.stat-card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 24px; box-shadow: var(--shadow-sm); }
.stat-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.icon-circle { width: 40px; height: 40px; border-radius: 50%; background: var(--color-primary-light); color: var(--color-primary); display: flex; align-items: center; justify-content: center; }
.change { font-size: 12px; font-weight: 600; color: var(--color-success); background: #E1F7EA; padding: 2px 8px; border-radius: 4px; }

.stat-value { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.stat-name { font-size: 14px; color: var(--color-text-secondary); font-weight: var(--font-weight-light); }

.chart-card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 24px; min-height: 300px; }
.chart-card h3 { font-size: 16px; margin-bottom: 24px; }
.chart-container { display: flex; gap: 16px; margin-top: 10px; }
.y-axis { display: flex; flex-direction: column; justify-content: space-between; font-size: 12px; color: var(--color-text-secondary); padding-bottom: 30px; /* offset for x-axis */ text-align: right; min-width: 20px; }
.chart-main { flex: 1; display: flex; flex-direction: column; }
.x-axis { display: flex; justify-content: space-between; padding-top: 8px; font-size: 11px; color: var(--color-text-secondary); border-top: 1px solid var(--color-border); }

.chart-box { height: 200px; display: flex; align-items: flex-end; }
.mock-bars { flex: 1; height: 100%; display: flex; align-items: flex-end; gap: 8px; }
.bar { flex: 1; background: var(--color-primary); border-radius: 4px 4px 0 0; opacity: 0.8; transition: height 1.0s cubic-bezier(0.4, 0, 0.2, 1); }
.bar:hover { opacity: 1; }
</style>

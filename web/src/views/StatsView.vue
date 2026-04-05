<script setup lang="ts">
import { BarChart, Clock, Database, TrendingUp, Activity } from 'lucide-vue-next';

// 模拟统计数据
const stats = [
  { name: '累计合成字数', value: '142.8k', change: '+12%', icon: Database },
  { name: '平均推理时延', value: '420ms', change: '-5%', icon: Clock },
  { name: '已存声纹模型', value: '12', change: '+2', icon: Activity },
  { name: '今日实时请求', value: '2.4k', change: '+18%', icon: TrendingUp },
];
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

    <!-- 模拟图表区 -->
    <div class="charts-row">
      <div class="chart-card">
        <h3>每秒实时推理吞吐量 (Requests/s)</h3>
        <div class="chart-box">
          <div class="mock-bars">
            <div v-for="n in 20" :key="n" class="bar" :style="{ height: Math.random()*100 + '%' }"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats { width: 100%; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 24px; margin-bottom: 32px; }

.stat-card { background: white; border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 24px; box-shadow: var(--shadow-sm); }
.stat-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.icon-circle { width: 40px; height: 40px; border-radius: 50%; background: var(--color-primary-light); color: var(--color-primary); display: flex; align-items: center; justify-content: center; }
.change { font-size: 12px; font-weight: 600; color: var(--color-success); background: #E1F7EA; padding: 2px 8px; border-radius: 4px; }

.stat-value { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.stat-name { font-size: 14px; color: var(--color-text-secondary); font-weight: var(--font-weight-light); }

.chart-card { background: white; border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 24px; min-height: 300px; }
.chart-card h3 { font-size: 16px; margin-bottom: 24px; }

.chart-box { height: 200px; display: flex; align-items: flex-end; padding-top: 20px; }
.mock-bars { flex: 1; height: 100%; display: flex; align-items: flex-end; gap: 8px; border-bottom: 1px solid var(--color-border); }
.bar { flex: 1; background: var(--color-primary); border-radius: 4px 4px 0 0; opacity: 0.8; transition: height 1s ease; }
.bar:hover { opacity: 1; }
</style>

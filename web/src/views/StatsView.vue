<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { BarChart, Clock, Database, TrendingUp, Activity, User as UserIcon } from 'lucide-vue-next';
import client from '../api/client';

const stats = ref<any[]>([]);
const throughput = ref<number[]>([]);
const ranking = ref<any[]>([]);
const isGlobal = ref(false);

const iconMap: any = { Database, Clock, Activity, TrendingUp };

const fetchData = async () => {
  try {
    const summary: any = await client.get('/stats/summary');
    isGlobal.value = summary.is_global;
    stats.value = summary.stats.map((s: any) => ({
      ...s,
      icon: iconMap[s.icon] || BarChart
    }));

    const tp: any = await client.get('/stats/throughput');
    throughput.value = (tp as any).data;

    // 如果是管理员，额外获取排名数据
    if (isGlobal.value) {
      const rankData: any = await client.get('/stats/admin/user-ranking');
      ranking.value = rankData.ranking;
    }
  } catch (err) {
    console.error('Failed to fetch stats:', err);
  }
};

onMounted(fetchData);
</script>

<template>
  <div class="stats">
    <div class="header">
      <h2>{{ isGlobal ? '系统全局运行状态' : '我的使用概览' }}</h2>
      <p>{{ isGlobal ? '实时监控 FastVox 引擎消耗与用户分布' : '查看您的个人语音合成消耗统计' }}</p>
    </div>

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

    <div class="charts-row">
      <!-- 吞吐量图表 -->
      <div class="card chart-card">
        <h3>每分钟实时推理吞吐量 (Requests/min)</h3>
        <div class="chart-container">
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
            <div class="x-axis">
              <span>{{ throughput.length }}min 前</span>
              <span>现在</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 用户排行榜 (仅管理员) -->
      <div v-if="isGlobal" class="card ranking-card">
        <h3>用户消耗排行榜 (Top 10)</h3>
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>用户</th>
                <th>消耗字数</th>
                <th>请求次数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in ranking" :key="user.email">
                <td>
                  <div class="user-info">
                    <UserIcon :size="14" />
                    <span>{{ user.name || '未命名用户' }}</span>
                  </div>
                </td>
                <td>{{ (user.chars / 1000).toFixed(1) }}k</td>
                <td>{{ user.requests }}</td>
              </tr>
              <tr v-if="ranking.length === 0">
                <td colspan="3" class="empty">暂无消耗记录</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats { width: 100%; max-width: 1400px; }
.header { margin-bottom: 32px; }
.header h2 { font-size: 24px; font-weight: 600; margin-bottom: 8px; }
.header p { color: var(--color-text-secondary); font-size: 14px; }

.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px; margin-bottom: 32px; }
.stat-card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 24px; box-shadow: var(--shadow-sm); }
.stat-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.icon-circle { width: 40px; height: 40px; border-radius: 50%; background: var(--color-primary-light); color: var(--color-primary); display: flex; align-items: center; justify-content: center; }
.change { font-size: 12px; font-weight: 600; color: var(--color-success); background: #E1F7EA; padding: 2px 8px; border-radius: 4px; }
.stat-value { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.stat-name { font-size: 14px; color: var(--color-text-secondary); font-weight: 500; }

.charts-row { display: grid; grid-template-columns: 1fr 400px; gap: 24px; align-items: start; }
@media (max-width: 1024px) {
  .charts-row { grid-template-columns: 1fr; }
}

.card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 24px; box-shadow: var(--shadow-sm); }
.chart-card h3, .ranking-card h3 { font-size: 16px; font-weight: 600; margin-bottom: 24px; }

.chart-container { display: flex; gap: 16px; margin-top: 10px; }
.y-axis { display: flex; flex-direction: column; justify-content: space-between; font-size: 12px; color: var(--color-text-secondary); padding-bottom: 24px; text-align: right; min-width: 24px; }
.chart-main { flex: 1; display: flex; flex-direction: column; }
.x-axis { display: flex; justify-content: space-between; padding-top: 8px; font-size: 11px; color: var(--color-text-secondary); border-top: 1px solid var(--color-border); }
.chart-box { height: 220px; display: flex; align-items: flex-end; padding-bottom: 4px; }
.mock-bars { flex: 1; height: 100%; display: flex; align-items: flex-end; gap: 4px; }
.bar { flex: 1; background: var(--color-primary); border-radius: 2px 2px 0 0; opacity: 0.8; transition: height 0.6s ease; }
.bar:hover { opacity: 1; }

.table-container { overflow-x: auto; }
.table { width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }
.table th { color: var(--color-text-secondary); font-weight: 500; padding: 12px 8px; border-bottom: 1px solid var(--color-border); font-size: 13px; }
.table td { padding: 12px 8px; border-bottom: 1px solid var(--color-border); color: var(--color-text-primary); }
.user-info { display: flex; align-items: center; gap: 8px; font-weight: 500; }
.empty { text-align: center; padding: 40px; color: var(--color-text-disabled); }
</style>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const clearance = ref(0)
onMounted(async () => {
  const data = await api('/allocate/latest?segment_id=1')
  rows.value = data.rejected || []
  clearance.value = data.clearance_m ?? 0
})
const category = (r: any) => r.reason_code === 'clearance' ? '净距不足' : '空档总长不够'
const badgeClass = (r: any) => r.reason_code === 'clearance' ? 'badge badge-warn' : 'badge badge-bad'
</script>
<template>
  <h1>放不下</h1>
  <p class="sub">当前摊间净距 {{ clearance }} m · 拒因互斥：净距不足 / 空档总长不够（不跨越挡柱）</p>
  <div class="card">
    <table>
      <thead><tr><th>摊主</th><th>需求宽度</th><th>类别</th><th>原因</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.vendor_id">
          <td>{{ r.vendor_name }}</td>
          <td>{{ r.width_m }}</td>
          <td><span :class="badgeClass(r)">{{ category(r) }}</span></td>
          <td>{{ r.reason }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!rows.length" class="muted">全部放下</p>
  </div>
</template>

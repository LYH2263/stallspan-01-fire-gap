<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
onMounted(async () => {
  const data = await api('/allocate/latest?segment_id=1')
  rows.value = data.rejected || []
})
function badge(code: string) {
  return code === 'clearance'
    ? { cls: 'badge-warn', text: '净距不足' }
    : { cls: 'badge-bad', text: '空档不够' }
}
</script>
<template>
  <h1>放不下</h1>
  <p class="sub">两类拒因互斥：净距不足（空档够但留不出摊间消防净距）／空档总长不够或跨挡柱</p>
  <div class="card">
    <table>
      <thead><tr><th>摊主</th><th>需求宽度</th><th>拒因类别</th><th>原因</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.vendor_id">
          <td>{{ r.vendor_name }}</td>
          <td>{{ r.width_m }}</td>
          <td><span class="badge" :class="badge(r.reason_code).cls">{{ badge(r.reason_code).text }}</span></td>
          <td>{{ r.reason }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!rows.length" class="muted">全部放下</p>
  </div>
</template>

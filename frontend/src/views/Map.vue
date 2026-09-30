<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
const data = ref<any>(null)
const vendors = ref<any[]>([])
async function run() { data.value = await api('/allocate/run?segment_id=1', { method: 'POST' }) }
onMounted(async () => {
  vendors.value = await api('/vendors')
  await run()
})
const colors = ['#e8a87c','#85dcb8','#e27d60','#c38d9e','#41b3a3','#f4a261','#e76f51']
const clearance = computed(() => data.value?.clearance_m ?? data.value?.segment?.clearance_m ?? 0)
const cells = computed(() => {
  if (!data.value) return []
  const width = data.value.segment.width_m
  const out: any[] = []
  for (const p of data.value.pillars || []) {
    out.push({ type: 'pillar', start: p.position_m - p.thickness_m/2, w: p.thickness_m, label: p.label || '挡柱' })
  }
  for (const [i, p] of (data.value.placements || []).entries()) {
    out.push({ type: 'stall', start: p.start_m, w: p.width_m, label: p.vendor_name, color: colors[i % colors.length] })
  }
  // 引擎实际占用的摊间净距空隙：图上空隙米数与引擎占用一致
  for (const g of data.value.clearance_gaps || []) {
    const w = Math.round((g.end_m - g.start_m) * 1000) / 1000
    out.push({ type: 'gap', start: g.start_m, w, label: `净距 ${w}m`, title: `摊间消防净距 ${w} m` })
  }
  return out.sort((a,b) => a.start - b.start).map(c => ({
    ...c,
    // 净距空隙严格按米数等比渲染，不做最小宽度放大
    pct: c.type === 'gap' ? (c.w / width) * 100 : Math.max((c.w / width) * 100, 2),
  }))
})
</script>
<template>
  <div class="ss-street-wrap">
    <h1>街段分配带</h1>
    <p class="sub">沿街一维开间 · 挡柱为竖直阻断 · 相邻两摊留 {{ clearance }} m 消防净距</p>
    <button class="btn" @click="run">重新分配</button>
    <div class="ss-band-ruler" v-if="data">
      <span>0 m</span>
      <span>{{ data.segment.name }} · {{ data.segment.width_m }} m · 净距 {{ clearance }} m</span>
      <span>{{ data.segment.width_m }} m</span>
    </div>
    <div class="ss-street-band" v-if="data">
      <div class="ss-street-inner">
        <div
          v-for="(c,i) in cells" :key="i"
          class="ss-band-cell"
          :class="{ 'ss-pillar': c.type === 'pillar', 'ss-gap': c.type === 'gap' }"
          :title="c.title"
          :style="{ width: c.pct + '%', background: c.type === 'stall' ? c.color : undefined, flex: '0 0 ' + c.pct + '%' }"
        >{{ c.type === 'gap' && c.pct < 3 ? '' : c.label }}</div>
      </div>
    </div>
    <div class="ss-band-legend" v-if="data && clearance > 0">
      <span class="ss-gap-swatch"></span> 摊间消防净距 {{ clearance }} m（与引擎占用一致）
    </div>
    <div class="ss-vendor-queue">
      <div v-for="v in vendors" :key="v.id" class="ss-vendor-chip">
        <strong>{{ v.name }}</strong>
        <span>需 {{ v.stall_width_m }} m · 优先 {{ v.priority }}</span>
      </div>
    </div>
    <div class="card" v-if="data">
      <table>
        <thead><tr><th>摊主</th><th>起点</th><th>终点</th><th>宽度</th></tr></thead>
        <tbody>
          <tr v-for="p in data.placements" :key="p.vendor_id">
            <td>{{ p.vendor_name }}</td><td>{{ p.start_m }}</td><td>{{ p.end_m }}</td><td>{{ p.width_m }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

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
const EPS = 1e-6
type Cell = { type: string; start: number; end: number; w: number; label: string; color?: string; gap?: boolean }
const cells = computed<Cell[]>(() => {
  if (!data.value) return []
  const width = data.value.segment.width_m
  const items: Cell[] = []
  for (const p of data.value.pillars || []) {
    items.push({ type: 'pillar', start: p.position_m - p.thickness_m / 2, end: p.position_m + p.thickness_m / 2,
      w: p.thickness_m, label: p.label || '挡柱' })
  }
  for (const [i, p] of (data.value.placements || []).entries()) {
    items.push({ type: 'stall', start: p.start_m, end: p.end_m, w: p.width_m,
      label: p.vendor_name, color: colors[i % colors.length] })
  }
  items.sort((a, b) => a.start - b.start)
  // 用引擎坐标铺绝对位置：空档照原样露出，仅给「两摊之间」的空隙标净距米数
  const out: Cell[] = []
  let cursor = 0
  let prev: Cell | null = null
  for (const it of items) {
    if (it.start > cursor + EPS) {
      const betweenStalls = prev?.type === 'stall' && it.type === 'stall'
      const gapM = Math.round((it.start - cursor) * 1000) / 1000
      out.push({ type: 'gap', start: cursor, end: it.start, w: gapM, gap: true,
        label: betweenStalls ? `净距 ${gapM}m` : '' })
    }
    out.push(it)
    cursor = Math.max(cursor, it.end)
    prev = it
  }
  if (width > cursor + EPS) {
    out.push({ type: 'gap', start: cursor, end: width, w: Math.round((width - cursor) * 1000) / 1000,
      gap: true, label: '' })
  }
  return out
})
function pos(c: Cell) {
  const width = data.value.segment.width_m
  return { left: (c.start / width) * 100 + '%', width: (c.w / width) * 100 + '%' }
}
// 每摊与前一摊之间的空隙米数，与图上标注、引擎占用同一口径；
// 两摊之间隔着挡柱（不在同一柱间空档）时不计摊间净距。
const gapBefore = computed<Record<number, string>>(() => {
  const m: Record<number, string> = {}
  const blocks = (data.value?.pillars || []).map((p: any) =>
    [p.position_m - p.thickness_m / 2, p.position_m + p.thickness_m / 2] as [number, number])
  const ps = [...(data.value?.placements || [])].sort((a: any, b: any) => a.start_m - b.start_m)
  ps.forEach((p: any, i: number) => {
    if (i === 0) { m[p.vendor_id] = '—'; return }
    const prev = ps[i - 1]
    const separatedByPillar = blocks.some(([lo, hi]: [number, number]) =>
      hi > prev.end_m + EPS && lo < p.start_m - EPS)
    if (separatedByPillar) { m[p.vendor_id] = '隔挡柱'; return }
    const g = Math.round((p.start_m - prev.end_m) * 1000) / 1000
    m[p.vendor_id] = g > EPS ? `${g} m` : '0（相接）'
  })
  return m
})
</script>
<template>
  <div class="ss-street-wrap">
    <h1>街段分配带</h1>
    <p class="sub">沿街一维开间 · 挡柱为竖直阻断 · 相邻两摊按街段消防净距留空（当前 {{ data?.clearance_m ?? 0 }} m）· 底部为摊主排队</p>
    <button class="btn" @click="run">重新分配</button>
    <div class="ss-band-ruler" v-if="data">
      <span>0 m</span>
      <span>{{ data.segment.name }} · 宽 {{ data.segment.width_m }} m · 摊间净距 {{ data.clearance_m }} m</span>
      <span>{{ data.segment.width_m }} m</span>
    </div>
    <div class="ss-street-band" v-if="data">
      <div class="ss-street-inner ss-street-abs">
        <div
          v-for="(c,i) in cells" :key="i"
          class="ss-band-cell"
          :class="{ 'ss-pillar': c.type === 'pillar', 'ss-gap': c.gap }"
          :style="{ ...pos(c), background: c.type === 'stall' ? c.color : undefined }"
        >
          <span v-if="c.label" :class="{ 'ss-gap-label': c.gap }">{{ c.label }}</span>
        </div>
      </div>
    </div>
    <div class="ss-vendor-queue">
      <div v-for="v in vendors" :key="v.id" class="ss-vendor-chip">
        <strong>{{ v.name }}</strong>
        <span>需 {{ v.stall_width_m }} m · 优先 {{ v.priority }}</span>
      </div>
    </div>
    <div class="card" v-if="data">
      <table>
        <thead><tr><th>摊主</th><th>起点</th><th>终点</th><th>宽度</th><th>与前摊空隙</th></tr></thead>
        <tbody>
          <tr v-for="p in [...data.placements].sort((a,b)=>a.start_m-b.start_m)" :key="p.vendor_id">
            <td>{{ p.vendor_name }}</td><td>{{ p.start_m }}</td><td>{{ p.end_m }}</td><td>{{ p.width_m }}</td>
            <td>{{ gapBefore[p.vendor_id] }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

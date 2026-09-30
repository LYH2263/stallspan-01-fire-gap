<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const saving = ref<number | null>(null)
const savedId = ref<number | null>(null)

async function load() { rows.value = await api('/segments') }
async function save(r: any) {
  const val = Number(r.clearance_m)
  if (!Number.isFinite(val) || val < 0) { alert('消防净距需为不小于 0 的数字（米）'); return }
  saving.value = r.id
  try {
    const updated = await api(`/segments/${r.id}`, {
      method: 'PATCH', body: JSON.stringify({ clearance_m: val }),
    })
    Object.assign(r, updated)
    savedId.value = r.id
    setTimeout(() => { if (savedId.value === r.id) savedId.value = null }, 2000)
  } finally {
    saving.value = null
  }
}
onMounted(load)
</script>
<template>
  <h1>街段</h1>
  <p class="sub">沿街可用宽度 · 相邻两摊消防净距（米，0 表示可端点相接连续塞档）</p>
  <div class="card">
    <table>
      <thead><tr><th>街段</th><th>宽度(m)</th><th>消防净距(m)</th><th>集日ID</th><th></th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.name }}</td>
          <td>{{ r.width_m }}</td>
          <td>
            <input
              v-model.number="r.clearance_m"
              type="number" min="0" step="0.1"
              style="width: 92px"
              @keyup.enter="save(r)"
            >
          </td>
          <td>{{ r.market_day_id }}</td>
          <td>
            <button class="btn" :disabled="saving === r.id" @click="save(r)">
              {{ saving === r.id ? '保存中…' : '保存' }}
            </button>
            <span v-if="savedId === r.id" class="badge badge-ok" style="margin-left:.5rem">已落库</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p class="muted" style="margin-bottom:0">改净距并保存后，再回分配图点「重新分配」即按新净距现算；放不下清单也会自动按新净距重算。</p>
  </div>
</template>

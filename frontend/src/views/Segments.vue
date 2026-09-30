<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const savedId = ref<number | null>(null)
const error = ref('')
async function load() { rows.value = await api('/segments') }
async function save(r: any) {
  error.value = ''
  const v = Number(r.clearance_m)
  if (!Number.isFinite(v) || v < 0) { error.value = `「${r.name}」净距不能为负数`; return }
  const updated = await api(`/segments/${r.id}`, {
    method: 'PATCH',
    body: JSON.stringify({ clearance_m: v }),
  })
  r.clearance_m = updated.clearance_m
  savedId.value = r.id
  setTimeout(() => { if (savedId.value === r.id) savedId.value = null }, 1600)
}
onMounted(load)
</script>
<template>
  <h1>街段</h1>
  <p class="sub">沿街可用宽度与摊间消防净距 · 净距保存后，分配图与放不下清单即按新净距现算</p>
  <div class="card">
    <table>
      <thead><tr><th>街段</th><th>宽度(m)</th><th>摊间净距(m)</th><th>集日ID</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.name }}</td>
          <td>{{ r.width_m }}</td>
          <td>
            <input
              v-model.number="r.clearance_m"
              type="number" min="0" step="0.1"
              class="ss-clearance-input"
              @keyup.enter="save(r)"
            />
            <div class="muted ss-clearance-hint">0 = 允许端点相接</div>
          </td>
          <td>{{ r.market_day_id }}</td>
          <td>
            <button class="btn" @click="save(r)">保存净距</button>
            <span v-if="savedId === r.id" class="badge badge-ok ss-saved">已保存</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="error" class="badge badge-bad">{{ error }}</p>
  </div>
</template>

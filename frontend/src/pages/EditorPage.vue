<script setup>
/**
 * File: EditorPage.vue
 * Description: Trilingual key-value editor with auto-save and cross-platform sync.
 * Author: zhangdadi
 * Created: 2026-03-10
 */

import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from '../i18n'

const apiBase = import.meta.env.VITE_API_BASE || ''
const { t } = useI18n()

const platform = ref('ios')
const relativePath = ref('')
const rows = ref([])
const loading = ref(false)
const saving = ref(false)
const searchKeyword = ref('')
const searchEnglish = ref('')
const uploadedLanguages = ref({
  en: false,
  ar: false,
  tr: false
})
const toast = ref({ show: false, type: 'success', message: '' })

const saveHintState = ref({ key: 'editor.hintEnabled', params: {} })
const saveHint = computed(() => t(saveHintState.value.key, saveHintState.value.params || {}))

const languageColumns = computed(() => ([
  { code: 'en', label: t('editor.columnEnglish') },
  { code: 'ar', label: t('editor.columnArabic') },
  { code: 'tr', label: t('editor.columnTurkish') }
]))

function setSaveHint(key, params = {}) {
  saveHintState.value = { key, params }
}

function getAuthHeaders() {
  const token = window.localStorage.getItem('auth_token') || ''
  if (!token) {
    return {}
  }
  return {
    Authorization: `Bearer ${token}`
  }
}

const hasAnyUploaded = computed(() => {
  return languageColumns.value.some((item) => uploadedLanguages.value[item.code])
})

const filteredRows = computed(() => {
  const keyKeyword = searchKeyword.value.trim().toLowerCase()
  const englishKeyword = searchEnglish.value.trim().toLowerCase()
  const indexed = rows.value.map((item, sourceIndex) => ({ item, sourceIndex }))
  if (!keyKeyword && !englishKeyword) {
    return indexed
  }
  return indexed.filter(({ item }) => {
    const keyMatched = !keyKeyword || (item.key || '').toLowerCase().includes(keyKeyword)
    const englishMatched = !englishKeyword || (item.en || '').toLowerCase().includes(englishKeyword)
    return keyMatched && englishMatched
  })
})

const pendingSave = ref(false)
const deleteConfirmVisible = ref(false)
const pendingDeleteIndex = ref(-1)
const pendingDeleteKeyName = ref(t('editor.keyEmpty'))
const lastSavedSignature = ref('')

function decorateRowsForDisplay(parsedRows, keys) {
  const decorated = parsedRows.map((item) => ({
    ...item,
    isNew: Boolean(item.key && keys.has(item.key))
  }))

  decorated.sort((a, b) => Number(Boolean(b.isNew)) - Number(Boolean(a.isNew)))
  return decorated
}

watch(platform, async () => {
  await fetchEditorTable()
})

function showToast(message, type = 'success') {
  toast.value = { show: true, type, message }
  window.clearTimeout(showToast.timer)
  showToast.timer = window.setTimeout(() => {
    toast.value.show = false
  }, 2400)
}

showToast.timer = 0

function resetUploadedLanguages() {
  uploadedLanguages.value = {
    en: false,
    ar: false,
    tr: false
  }
}

function getPlatformLabel(code) {
  return code === 'ios' ? 'iOS' : 'android'
}

function getClockText() {
  const now = new Date()
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
}

function buildRowsPayload() {
  return rows.value.map((item) => ({
    key: item.key || '',
    en: item.en || '',
    ar: item.ar || '',
    tr: item.tr || ''
  }))
}

function buildRowsSignature(payloadRows) {
  return JSON.stringify({
    platform: platform.value,
    relative_path: relativePath.value,
    rows: payloadRows
  })
}

function markEditing() {
  if (!relativePath.value || !hasAnyUploaded.value) {
    return
  }
  setSaveHint('editor.hintEditing')
}

function triggerAutoSave() {
  void saveEditorTable({ auto: true })
}

async function fetchEditorTable() {
  loading.value = true
  cancelRemoveRow()

  try {
    const query = new URLSearchParams({ platform: platform.value })
    const response = await fetch(`${apiBase}/api/editor-table?${query.toString()}`, {
      credentials: 'include',
      headers: getAuthHeaders()
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || t('editor.toastLoadFailed'))
    }

    const data = await response.json()
    relativePath.value = data.relative_path || ''
    uploadedLanguages.value = data.uploaded_languages || { en: false, ar: false, tr: false }
    const newKeys = Array.isArray(data.new_keys)
      ? data.new_keys.filter((item) => typeof item === 'string' && item.trim())
      : []
    const newKeySet = new Set(newKeys)

    const parsedRows = Array.isArray(data.rows) ? data.rows : []
    const normalizedRows = parsedRows.map((item) => ({
      key: item.key || '',
      en: item.en || '',
      ar: item.ar || '',
      tr: item.tr || ''
    }))

    rows.value = normalizedRows.length
      ? decorateRowsForDisplay(normalizedRows, newKeySet)
      : [{ key: '', en: '', ar: '', tr: '', isNew: false }]
    lastSavedSignature.value = buildRowsSignature(buildRowsPayload())

    if (relativePath.value && hasAnyUploaded.value) {
      setSaveHint('editor.hintEnabled')
    } else {
      setSaveHint('editor.hintNoTarget')
    }
  } catch (error) {
    relativePath.value = ''
    resetUploadedLanguages()
    rows.value = [{ key: '', en: '', ar: '', tr: '', isNew: false }]
    lastSavedSignature.value = ''
    setSaveHint('editor.hintUnavailable')
    showToast(error.message || t('editor.toastLoadFailed'), 'error')
  } finally {
    loading.value = false
  }
}

function addRow() {
  rows.value.unshift({ key: '', en: '', ar: '', tr: '', isNew: true })
  triggerAutoSave()
}

function removeRow(index) {
  if (rows.value.length === 1) {
    rows.value[0] = { key: '', en: '', ar: '', tr: '', isNew: false }
  } else {
    rows.value.splice(index, 1)
  }
  triggerAutoSave()
}

function requestRemoveRow(index) {
  const keyName = (rows.value[index]?.key || '').trim()
  pendingDeleteKeyName.value = keyName || t('editor.keyEmpty')
  pendingDeleteIndex.value = index
  deleteConfirmVisible.value = true
}

function cancelRemoveRow() {
  deleteConfirmVisible.value = false
  pendingDeleteIndex.value = -1
  pendingDeleteKeyName.value = t('editor.keyEmpty')
}

function confirmRemoveRow() {
  const index = pendingDeleteIndex.value
  cancelRemoveRow()
  if (index < 0 || index >= rows.value.length) {
    return
  }
  removeRow(index)
}

function getValuePlaceholder(code) {
  if (uploadedLanguages.value[code]) {
    return t('editor.valuePlaceholder')
  }
  return t('editor.valueMissingPlaceholder')
}

async function saveEditorTable({ auto = false } = {}) {
  if (!relativePath.value || !hasAnyUploaded.value) {
    return
  }

  const payloadRows = buildRowsPayload()
  const currentSignature = buildRowsSignature(payloadRows)
  if (currentSignature === lastSavedSignature.value) {
    if (auto) {
      setSaveHint('editor.hintNoChanges', { time: getClockText() })
    }
    return
  }

  if (saving.value) {
    pendingSave.value = true
    return
  }

  saving.value = true
  setSaveHint('editor.hintSaving')

  try {
    const response = await fetch(`${apiBase}/api/editor-table`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        platform: platform.value,
        relative_path: relativePath.value,
        rows: payloadRows
      })
    })

    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data.detail || t('editor.toastSaveFailed'))
    }

    const syncInfo = data.cross_platform_sync || {}
    const syncedRows = Number(syncInfo.synced_rows || 0)
    const targetPlatform = syncInfo.target_platform ? getPlatformLabel(syncInfo.target_platform) : ''

    if (syncedRows > 0 && targetPlatform) {
      setSaveHint('editor.hintSavedSynced', {
        count: syncedRows,
        platform: targetPlatform,
        time: getClockText()
      })
    } else {
      setSaveHint('editor.hintSaved', { time: getClockText() })
    }
    lastSavedSignature.value = currentSignature

    if (!auto) {
      showToast(t('editor.toastSaved'))
    }
  } catch (error) {
    setSaveHint('editor.hintSaveFailed')
    showToast(error.message || t('editor.toastSaveFailed'), 'error')
  } finally {
    saving.value = false
    if (pendingSave.value) {
      pendingSave.value = false
      void saveEditorTable({ auto: true })
    }
  }
}

onMounted(() => {
  fetchEditorTable()
})
</script>

<template>
  <section class="card editor-card">
    <div class="head-row">
      <h2><i class="fa-solid fa-pen-to-square"></i> {{ t('editor.title') }}</h2>
      <div class="platform-switch">
        <button :class="{ active: platform === 'ios' }" @click="platform = 'ios'">
          <i class="fa-brands fa-apple"></i>
          iOS
        </button>
        <button :class="{ active: platform === 'android' }" @click="platform = 'android'">
          <i class="fa-brands fa-android"></i>
          android
        </button>
      </div>
    </div>

    <div class="meta-box">
      <div class="status-row">
        <span
          v-for="item in languageColumns"
          :key="item.code"
          class="status-pill"
          :class="uploadedLanguages[item.code] ? 'ok' : 'off'"
        >
          {{ item.label }}: {{ uploadedLanguages[item.code] ? t('editor.uploaded') : t('editor.notUploaded') }}
        </span>
      </div>
      <p class="feature-note">
        {{ t('editor.featureNote') }}
      </p>
    </div>

    <div v-if="loading" class="empty-state">{{ t('editor.loading') }}</div>
    <div v-else-if="!relativePath" class="empty-state">
      {{ t('editor.noEditableFile') }}
    </div>
    <div v-else class="editor-wrap">
      <div class="toolbar">
        <div class="search-group">
          <div class="search-box">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input v-model="searchKeyword" :placeholder="t('editor.searchByKey')" />
          </div>
          <div class="search-box">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input v-model="searchEnglish" :placeholder="t('editor.searchByEnglish')" />
          </div>
        </div>
        <div class="toolbar-actions">
          <button class="text-btn" :disabled="loading" @click="fetchEditorTable">
            <i class="fa-solid fa-rotate"></i>
            {{ t('editor.refresh') }}
          </button>
          <button class="text-btn" @click="addRow">
            <i class="fa-solid fa-plus"></i>
            {{ t('editor.addKey') }}
          </button>
        </div>
      </div>

      <p class="save-status" :class="{ saving: saving }">{{ saveHint }}</p>

      <div class="kv-head">
        <span>{{ t('editor.columnKey') }}</span>
        <span>{{ t('editor.columnEnglish') }}</span>
        <span>{{ t('editor.columnArabic') }}</span>
        <span>{{ t('editor.columnTurkish') }}</span>
        <span>{{ t('editor.columnActions') }}</span>
      </div>

      <div class="kv-list">
        <div class="kv-row" v-for="{ item, sourceIndex } in filteredRows" :key="`row-${sourceIndex}`">
          <div class="key-cell">
            <span v-if="item.isNew" class="new-tag">{{ t('editor.newTag') }}</span>
            <input
              v-model="item.key"
              class="field key-field"
              :placeholder="t('editor.keyExample')"
              @input="markEditing"
              @blur="triggerAutoSave"
            />
          </div>
          <textarea
            v-model="item.en"
            :disabled="!uploadedLanguages.en"
            class="field value-field"
            rows="2"
            :placeholder="getValuePlaceholder('en')"
            @input="markEditing"
            @blur="triggerAutoSave"
          ></textarea>
          <textarea
            v-model="item.ar"
            :disabled="!uploadedLanguages.ar"
            class="field value-field"
            rows="2"
            :placeholder="getValuePlaceholder('ar')"
            @input="markEditing"
            @blur="triggerAutoSave"
          ></textarea>
          <textarea
            v-model="item.tr"
            :disabled="!uploadedLanguages.tr"
            class="field value-field"
            rows="2"
            :placeholder="getValuePlaceholder('tr')"
            @input="markEditing"
            @blur="triggerAutoSave"
          ></textarea>
          <button class="remove-btn" @click="requestRemoveRow(sourceIndex)">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>
    </div>

    <div v-if="deleteConfirmVisible" class="confirm-mask" @click.self="cancelRemoveRow">
      <div class="confirm-dialog">
        <h3>{{ t('editor.deleteConfirmTitle', { key: pendingDeleteKeyName }) }}</h3>
        <p>{{ t('editor.deleteConfirmBody') }}</p>
        <div class="confirm-actions">
          <button class="dialog-btn ghost" @click="cancelRemoveRow">{{ t('editor.cancel') }}</button>
          <button class="dialog-btn danger" @click="confirmRemoveRow">{{ t('editor.delete') }}</button>
        </div>
      </div>
    </div>

    <transition name="toast-fade">
      <div v-if="toast.show" class="toast" :class="toast.type">
        <i :class="toast.type === 'error' ? 'fa-solid fa-circle-exclamation' : 'fa-solid fa-circle-check'"></i>
        <span>{{ toast.message }}</span>
      </div>
    </transition>
  </section>
</template>

<style scoped>
.card {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(15, 118, 110, 0.2);
  border-radius: 18px;
  box-shadow: 0 14px 24px rgba(18, 32, 38, 0.12);
  backdrop-filter: blur(4px);
}

.editor-card {
  padding: 16px;
}

.head-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.head-row h2 {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 1.08rem;
}

.platform-switch {
  display: inline-flex;
  gap: 8px;
  flex-wrap: wrap;
}

.platform-switch button {
  border: 0;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 700;
  color: #3f545e;
  background: #e5efed;
}

.platform-switch button.active {
  background: linear-gradient(120deg, #0f766e, #0b5f59);
  color: #ecfffc;
}

.meta-box {
  margin-top: 12px;
  border-radius: 12px;
  padding: 12px;
  background: rgba(15, 118, 110, 0.12);
}

.meta-box p {
  margin: 0;
  color: #304c56;
}

.feature-note {
  margin-top: 10px !important;
  padding-top: 10px;
  border-top: 1px dashed rgba(15, 118, 110, 0.25);
  color: #3f5b65 !important;
  font-size: 0.88rem;
  line-height: 1.6;
}

.status-row {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-pill {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.84rem;
  font-weight: 700;
}

.status-pill.ok {
  background: rgba(15, 118, 110, 0.2);
  color: #0d5d56;
}

.status-pill.off {
  background: rgba(217, 72, 15, 0.14);
  color: #95380c;
}

.editor-wrap {
  margin-top: 14px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.search-group {
  display: inline-flex;
  gap: 8px;
  flex-wrap: wrap;
}

.search-box {
  min-width: 220px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(65, 83, 92, 0.22);
  border-radius: 10px;
  background: #f8fbfc;
  padding: 0 10px;
}

.search-box input {
  width: 100%;
  border: 0;
  outline: none;
  background: transparent;
  padding: 9px 0;
}

.toolbar-actions {
  display: inline-flex;
  gap: 8px;
}

.text-btn,
.remove-btn {
  border: 0;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  cursor: pointer;
}

.text-btn {
  padding: 8px 12px;
  color: #0f766e;
  background: rgba(15, 118, 110, 0.15);
}

.text-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.save-status {
  margin: 10px 0 0;
  color: #4f6872;
  font-size: 0.9rem;
}

.save-status.saving {
  color: #0f766e;
  font-weight: 700;
}

.kv-head,
.kv-row {
  margin-top: 10px;
  display: grid;
  grid-template-columns: minmax(280px, 24%) repeat(3, minmax(220px, 1fr)) 56px;
  gap: 8px;
  align-items: start;
}

.kv-head {
  margin-top: 12px;
  color: #55707a;
  font-size: 0.85rem;
  font-weight: 700;
}

.kv-list {
  max-height: 560px;
  overflow: auto;
  padding-right: 4px;
}

.field {
  border: 1px solid rgba(65, 83, 92, 0.22);
  border-radius: 10px;
  background: #fbfefe;
  color: #132126;
  padding: 9px;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.key-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.key-field {
  flex: 1;
  min-width: 0;
}

.new-tag {
  width: fit-content;
  padding: 2px 8px;
  border-radius: 999px;
  background: linear-gradient(120deg, #ea580c, #cc4d0e);
  color: #fff6ef;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.4px;
}

.field:focus {
  border-color: rgba(15, 118, 110, 0.72);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.16);
}

.value-field {
  resize: vertical;
  line-height: 1.6;
  min-height: 74px;
}

.field:disabled {
  background: #edf3f5;
  color: #8aa0a9;
}

.remove-btn {
  justify-content: center;
  padding: 9px;
  color: #fff;
  background: #d94f31;
}

.confirm-mask {
  position: fixed;
  inset: 0;
  z-index: 60;
  padding: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(8, 16, 20, 0.42);
}

.confirm-dialog {
  width: min(420px, 94vw);
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(15, 118, 110, 0.2);
  background: #fdfefe;
  box-shadow: 0 18px 28px rgba(18, 32, 38, 0.22);
}

.confirm-dialog h3 {
  margin: 0;
  font-size: 1rem;
  color: #132126;
}

.confirm-dialog p {
  margin: 8px 0 0;
  color: #4f6872;
  font-size: 0.9rem;
}

.confirm-actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.dialog-btn {
  border: 0;
  border-radius: 10px;
  padding: 8px 12px;
  font-weight: 700;
  cursor: pointer;
}

.dialog-btn.ghost {
  color: #35505a;
  background: #e6eff2;
}

.dialog-btn.danger {
  color: #fff6f2;
  background: linear-gradient(120deg, #d9480f, #b53a0c);
}

.empty-state {
  margin-top: 12px;
  border-radius: 10px;
  padding: 16px 12px;
  text-align: center;
  background: rgba(65, 83, 92, 0.08);
  color: #57717a;
}

.toast {
  position: fixed;
  right: 20px;
  bottom: 22px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 10px 14px;
  border-radius: 12px;
  color: #f3fcff;
  box-shadow: 0 14px 24px rgba(18, 32, 38, 0.18);
}

.toast.success {
  background: linear-gradient(120deg, #0f766e, #0b5f59);
}

.toast.error {
  background: linear-gradient(120deg, #d9480f, #a0350b);
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.2s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 1120px) {
  .kv-head,
  .kv-row {
    grid-template-columns: 1fr;
  }

  .kv-head span:last-child {
    display: none;
  }

  .remove-btn {
    width: fit-content;
  }
}

@media (max-width: 640px) {
  .editor-card {
    padding: 12px;
  }

  .toast {
    right: 10px;
    left: 10px;
    bottom: 12px;
    justify-content: center;
  }
}
</style>

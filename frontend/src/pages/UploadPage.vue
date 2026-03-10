<script setup>
/**
 * File: UploadPage.vue
 * Description: Upload, list, and download translation files by platform/language.
 * Author: zhangdadi
 * Created: 2026-03-10
 */

import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from '../i18n'

const apiBase = import.meta.env.VITE_API_BASE || ''
const { t } = useI18n()

const platform = ref('ios')
const language = ref('en')
const uploadFiles = ref([])
const dragActive = ref(false)
const files = ref([])
const loadingFiles = ref(false)
const uploading = ref(false)
const toast = ref({ show: false, type: 'success', message: '' })
const editDialog = ref({
  show: false,
  mode: 'edit',
  loading: false,
  saving: false,
  relativePath: '',
  content: '',
  originalContent: ''
})

const languageOptions = computed(() => ([
  { code: 'en', label: t('upload.languageEnglish') },
  { code: 'ar', label: t('upload.languageArabic') },
  { code: 'tr', label: t('upload.languageTurkish') }
]))

function getAuthHeaders() {
  const token = window.localStorage.getItem('auth_token') || ''
  if (!token) {
    return {}
  }
  return {
    Authorization: `Bearer ${token}`
  }
}

const pendingUploadNames = computed(() => uploadFiles.value.map((item) => item.name).join(', '))
const hasEditChanges = computed(() => editDialog.value.content !== editDialog.value.originalContent)
const isAppendMode = computed(() => editDialog.value.mode === 'append')
const canSaveDialog = computed(() => {
  if (isAppendMode.value) {
    return Boolean(editDialog.value.content.trim())
  }
  return hasEditChanges.value
})
const editFileName = computed(() => {
  const relativePath = editDialog.value.relativePath
  if (!relativePath) {
    return '--'
  }
  return relativePath.split('/').pop() || relativePath
})
const dialogTitle = computed(() => {
  if (isAppendMode.value) {
    return t('upload.appendDialogTitle', { name: editFileName.value })
  }
  return t('upload.editDialogTitle', { name: editFileName.value })
})
const dialogPlaceholder = computed(() => {
  if (isAppendMode.value) {
    return t('upload.appendPlaceholder')
  }
  return t('upload.editPlaceholder')
})
const appendExample = computed(() => {
  if (platform.value === 'ios') {
    return t('upload.appendExampleIos')
  }
  return t('upload.appendExampleAndroid')
})

watch([platform, language], async () => {
  await fetchFiles()
})

function showToast(message, type = 'success') {
  toast.value = { show: true, type, message }
  window.clearTimeout(showToast.timer)
  showToast.timer = window.setTimeout(() => {
    toast.value.show = false
  }, 2400)
}

showToast.timer = 0

async function fetchFiles() {
  loadingFiles.value = true
  try {
    const query = new URLSearchParams({
      platform: platform.value,
      language: language.value
    })
    const response = await fetch(`${apiBase}/api/files?${query.toString()}`, {
      credentials: 'include',
      headers: getAuthHeaders()
    })
    if (!response.ok) {
      throw new Error(t('upload.toastLoadFileListFailed'))
    }
    const data = await response.json()
    files.value = data.files || []
  } catch (error) {
    showToast(error.message || t('upload.toastLoadFileListFailed'), 'error')
  } finally {
    loadingFiles.value = false
  }
}

function onFileSelect(event) {
  const fileList = event.target.files
  if (!fileList?.length) {
    return
  }
  uploadFiles.value = Array.from(fileList)
}

function onDragOver(event) {
  event.preventDefault()
  dragActive.value = true
}

function onDragLeave() {
  dragActive.value = false
}

function onDrop(event) {
  event.preventDefault()
  dragActive.value = false
  const fileList = event.dataTransfer?.files
  if (!fileList?.length) {
    return
  }
  uploadFiles.value = Array.from(fileList)
}

function validateFileType(fileName) {
  const lower = fileName.toLowerCase()
  if (platform.value === 'ios') {
    return lower.endsWith('.strings')
  }
  return lower.endsWith('.xml')
}

async function uploadSelectedFiles() {
  if (!uploadFiles.value.length) {
    showToast(t('upload.toastSelectFile'), 'error')
    return
  }

  const invalidFile = uploadFiles.value.find((item) => !validateFileType(item.name))
  if (invalidFile) {
    const tip = platform.value === 'ios' ? t('upload.toastInvalidIosTip') : t('upload.toastInvalidAndroidTip')
    showToast(t('upload.toastInvalidFileType', { name: invalidFile.name, tip }), 'error')
    return
  }

  uploading.value = true
  try {
    for (const item of uploadFiles.value) {
      const formData = new FormData()
      formData.append('platform', platform.value)
      formData.append('language', language.value)
      formData.append('upload_file', item)

      const response = await fetch(`${apiBase}/api/upload`, {
        method: 'POST',
        credentials: 'include',
        headers: getAuthHeaders(),
        body: formData
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || t('upload.toastUploadSingleFailed', { name: item.name }))
      }
    }

    uploadFiles.value = []
    showToast(t('upload.toastUploadSuccess'))
    await fetchFiles()
  } catch (error) {
    showToast(error.message || t('upload.toastUploadFailed'), 'error')
  } finally {
    uploading.value = false
  }
}

function formatSize(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatTime(iso) {
  const value = new Date(iso)
  if (Number.isNaN(value.getTime())) {
    return '--'
  }
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')} ${String(value.getHours()).padStart(2, '0')}:${String(value.getMinutes()).padStart(2, '0')}`
}

async function downloadFile(relativePath) {
  try {
    const query = new URLSearchParams({
      platform: platform.value,
      language: language.value,
      relative_path: relativePath
    })
    const response = await fetch(`${apiBase}/api/download?${query.toString()}`, {
      credentials: 'include',
      headers: getAuthHeaders()
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || t('upload.toastDownloadFailed'))
    }

    const blob = await response.blob()
    const objectUrl = window.URL.createObjectURL(blob)
    const fileName = relativePath.split('/').pop() || 'download'

    const link = document.createElement('a')
    link.href = objectUrl
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(objectUrl)
  } catch (error) {
    showToast(error.message || t('upload.toastDownloadFailed'), 'error')
  }
}

function closeEditDialog() {
  if (editDialog.value.saving) {
    return
  }
  editDialog.value.show = false
}

async function openEditDialog(relativePath) {
  editDialog.value = {
    show: true,
    mode: 'edit',
    loading: true,
    saving: false,
    relativePath,
    content: '',
    originalContent: ''
  }
  try {
    const query = new URLSearchParams({
      platform: platform.value,
      language: language.value,
      relative_path: relativePath
    })
    const response = await fetch(`${apiBase}/api/file-content?${query.toString()}`, {
      credentials: 'include',
      headers: getAuthHeaders()
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || t('upload.toastReadFileFailed'))
    }
    const data = await response.json()
    const content = typeof data.content === 'string' ? data.content : ''
    editDialog.value.content = content
    editDialog.value.originalContent = content
  } catch (error) {
    showToast(error.message || t('upload.toastReadFileFailed'), 'error')
    editDialog.value.show = false
  } finally {
    editDialog.value.loading = false
  }
}

function openAppendDialog(relativePath) {
  editDialog.value = {
    show: true,
    mode: 'append',
    loading: false,
    saving: false,
    relativePath,
    content: '',
    originalContent: ''
  }
}

async function saveEditedFile() {
  if (editDialog.value.loading || editDialog.value.saving || !editDialog.value.relativePath) {
    return
  }
  editDialog.value.saving = true
  try {
    if (isAppendMode.value) {
      const response = await fetch(`${apiBase}/api/file-content/append`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          platform: platform.value,
          language: language.value,
          relative_path: editDialog.value.relativePath,
          content: editDialog.value.content
        })
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data.detail || t('upload.toastAppendFailed'))
      }
      const addedCount = Number(data.added_keys_count || 0)
      const updatedCount = Number(data.updated_keys_count || 0)
      showToast(t('upload.toastAppendSuccess', { added: addedCount, updated: updatedCount }))
      editDialog.value.show = false
    } else {
      const response = await fetch(`${apiBase}/api/file-content`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          platform: platform.value,
          language: language.value,
          relative_path: editDialog.value.relativePath,
          content: editDialog.value.content
        })
      })
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || t('upload.toastSaveFileFailed'))
      }
      editDialog.value.originalContent = editDialog.value.content
      showToast(t('upload.toastSaveFileSuccess'))
    }
    await fetchFiles()
  } catch (error) {
    const fallback = isAppendMode.value ? t('upload.toastAppendFailed') : t('upload.toastSaveFileFailed')
    showToast(error.message || fallback, 'error')
  } finally {
    editDialog.value.saving = false
  }
}

async function copyEditContent() {
  try {
    const text = editDialog.value.content || ''
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      showToast(t('upload.toastCopySuccess'))
      return
    }

    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const copied = document.execCommand('copy')
    document.body.removeChild(textarea)
    if (!copied) {
      throw new Error(t('upload.toastCopyFailed'))
    }
    showToast(t('upload.toastCopySuccess'))
  } catch (error) {
    showToast(error.message || t('upload.toastCopyFailed'), 'error')
  }
}

onMounted(() => {
  fetchFiles()
})
</script>

<template>
  <div class="page-grid">
    <section class="card upload-card">
      <div class="section-head">
        <h2><i class="fa-solid fa-cloud-arrow-up"></i> {{ t('upload.sourceTitle') }}</h2>
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

      <div class="language-switch">
        <button
          v-for="item in languageOptions"
          :key="item.code"
          :class="{ active: language === item.code }"
          @click="language = item.code"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="upload-tip">
        {{ t('upload.supportedTip') }}
      </div>

      <div
        class="drop-zone"
        :class="{ active: dragActive }"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
      >
        <i class="fa-solid fa-file-arrow-up"></i>
        <p>{{ t('upload.dragHint') }}</p>
        <p class="drop-help">{{ t('upload.dragHelp') }}</p>
        <input id="upload-input" type="file" multiple @change="onFileSelect" />
        <label class="pick-btn" for="upload-input">
          <i class="fa-solid fa-folder-open"></i>
          {{ t('upload.selectFiles') }}
        </label>
      </div>

      <div class="upload-foot">
        <span class="pending-text">{{ pendingUploadNames || t('upload.noFilesSelected') }}</span>
        <button class="submit-btn" :disabled="uploading" @click="uploadSelectedFiles">
          <i class="fa-solid fa-upload"></i>
          {{ uploading ? t('upload.uploading') : t('upload.uploadReplace') }}
        </button>
      </div>
    </section>

    <section class="card list-card">
      <div class="section-head">
        <h2><i class="fa-solid fa-folder-tree"></i> {{ t('upload.uploadedTitle') }}</h2>
        <span class="hint">{{ t('upload.filesCount', { count: files.length }) }}</span>
      </div>

      <div v-if="loadingFiles" class="empty-state">{{ t('upload.loadingList') }}</div>
      <div v-else-if="!files.length" class="empty-state">{{ t('upload.emptyList') }}</div>
      <ul v-else class="file-list">
        <li v-for="item in files" :key="item.relative_path">
          <div class="top-line">
            <span class="path">{{ item.relative_path }}</span>
            <span class="size">{{ formatSize(item.size) }}</span>
          </div>
          <div class="file-meta">
            <div class="time">{{ formatTime(item.updated_at) }}</div>
            <div class="file-actions">
              <button class="append-btn" @click="openAppendDialog(item.relative_path)">
                <i class="fa-solid fa-plus"></i>
                {{ t('upload.append') }}
              </button>
              <button class="edit-btn" @click="openEditDialog(item.relative_path)">
                <i class="fa-solid fa-pen-to-square"></i>
                {{ t('upload.edit') }}
              </button>
              <button class="download-btn" @click="downloadFile(item.relative_path)">
                <i class="fa-solid fa-download"></i>
                {{ t('upload.download') }}
              </button>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <div v-if="editDialog.show" class="modal-mask" @click.self="closeEditDialog">
      <section class="edit-modal">
        <header class="edit-head">
          <h3>{{ dialogTitle }}</h3>
          <button class="close-btn" :disabled="editDialog.saving" @click="closeEditDialog">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </header>

        <div v-if="editDialog.loading" class="modal-loading">
          {{ t('upload.loadingFileContent') }}
        </div>
        <textarea
          v-else
          v-model="editDialog.content"
          class="edit-textarea"
          spellcheck="false"
          :placeholder="dialogPlaceholder"
        ></textarea>
        <div v-if="!editDialog.loading && isAppendMode" class="append-tip">
          <p>{{ t('upload.appendTip') }}</p>
          <pre class="append-sample">{{ appendExample }}</pre>
        </div>

        <footer class="edit-foot">
          <button class="copy-btn" :disabled="editDialog.loading" @click="copyEditContent">
            <i class="fa-solid fa-copy"></i>
            {{ t('upload.copy') }}
          </button>
          <div class="foot-right">
            <button class="ghost-btn" :disabled="editDialog.saving" @click="closeEditDialog">
              {{ t('upload.cancelEdit') }}
            </button>
            <button
              class="save-btn"
              :disabled="editDialog.loading || editDialog.saving || !canSaveDialog"
              @click="saveEditedFile"
            >
              <i class="fa-solid fa-floppy-disk"></i>
              {{
                editDialog.saving
                  ? (isAppendMode ? t('upload.appendingContent') : t('upload.savingFileContent'))
                  : (isAppendMode ? t('upload.appendSave') : t('upload.saveEdit'))
              }}
            </button>
          </div>
        </footer>
      </section>
    </div>

    <transition name="toast-fade">
      <div v-if="toast.show" class="toast" :class="toast.type">
        <i :class="toast.type === 'error' ? 'fa-solid fa-circle-exclamation' : 'fa-solid fa-circle-check'"></i>
        <span>{{ toast.message }}</span>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.page-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: 14px;
}

.card {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(15, 118, 110, 0.2);
  border-radius: 18px;
  box-shadow: 0 14px 24px rgba(18, 32, 38, 0.12);
  backdrop-filter: blur(4px);
}

.upload-card,
.list-card {
  padding: 16px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.section-head h2 {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 1.08rem;
}

.platform-switch,
.language-switch {
  display: inline-flex;
  gap: 8px;
  flex-wrap: wrap;
}

.language-switch {
  margin-top: 12px;
}

.platform-switch button,
.language-switch button {
  border: 0;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 700;
  color: #3f545e;
  background: #e5efed;
}

.platform-switch button.active,
.language-switch button.active {
  background: linear-gradient(120deg, #0f766e, #0b5f59);
  color: #ecfffc;
}

.upload-tip {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(15, 118, 110, 0.12);
  color: #35505a;
  font-size: 0.9rem;
}

.drop-zone {
  margin-top: 12px;
  border: 2px dashed rgba(15, 118, 110, 0.35);
  border-radius: 14px;
  text-align: center;
  padding: 24px 14px;
  background: linear-gradient(145deg, rgba(238, 250, 247, 0.95), rgba(247, 252, 251, 0.9));
  transition: all 0.2s ease;
}

.drop-zone.active {
  border-color: #0f766e;
  transform: translateY(-1px);
}

.drop-zone i {
  font-size: 1.9rem;
  color: #0f766e;
}

.drop-zone p {
  margin: 8px 0 0;
}

.drop-help {
  color: #56707a;
  font-size: 0.9rem;
}

#upload-input {
  width: 0;
  height: 0;
  opacity: 0;
  position: absolute;
}

.pick-btn,
.submit-btn {
  border: 0;
  border-radius: 10px;
  padding: 9px 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  cursor: pointer;
}

.pick-btn {
  margin-top: 12px;
  color: #0f766e;
  background: rgba(15, 118, 110, 0.15);
}

.upload-foot {
  margin-top: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.pending-text {
  color: #526973;
  font-size: 0.9rem;
}

.submit-btn {
  color: #fff8f3;
  background: linear-gradient(120deg, #ea580c, #cc4d0e);
  box-shadow: 0 8px 14px rgba(204, 77, 14, 0.35);
}

.submit-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.hint {
  color: #57717a;
  font-size: 0.88rem;
}

.file-list {
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 520px;
  overflow: auto;
}

.file-list li {
  border: 1px solid rgba(15, 118, 110, 0.2);
  border-radius: 10px;
  padding: 10px;
  background: #f5faf9;
}

.top-line {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.path {
  font-weight: 700;
  word-break: break-all;
}

.size,
.time {
  font-size: 0.82rem;
  color: #58727c;
}

.file-meta {
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.file-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.append-btn,
.edit-btn,
.download-btn {
  border: 0;
  border-radius: 8px;
  padding: 6px 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  color: #0f766e;
  background: rgba(15, 118, 110, 0.14);
  cursor: pointer;
}

.append-btn {
  color: #1f6d19;
  background: rgba(34, 197, 94, 0.18);
}

.edit-btn {
  color: #0f4f7a;
  background: rgba(10, 132, 255, 0.15);
}

.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(13, 25, 31, 0.46);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.edit-modal {
  width: min(860px, 100%);
  border-radius: 14px;
  border: 1px solid rgba(15, 118, 110, 0.26);
  background: linear-gradient(145deg, #f5fbf9, #eef6f5);
  box-shadow: 0 16px 32px rgba(17, 31, 37, 0.28);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.edit-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.edit-head h3 {
  margin: 0;
  font-size: 1rem;
  color: #28434d;
}

.close-btn {
  border: 0;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: rgba(65, 83, 92, 0.12);
  color: #38525c;
  cursor: pointer;
}

.close-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.modal-loading {
  border-radius: 10px;
  padding: 16px 12px;
  text-align: center;
  color: #526973;
  background: rgba(15, 118, 110, 0.1);
}

.edit-textarea {
  width: 100%;
  min-height: 340px;
  border: 1px solid rgba(15, 118, 110, 0.24);
  border-radius: 10px;
  padding: 12px;
  resize: vertical;
  font-family: 'Menlo', 'Consolas', 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.5;
  color: #263d47;
  background: #ffffff;
}

.edit-textarea:focus {
  outline: 2px solid rgba(15, 118, 110, 0.24);
}

.append-tip {
  margin-top: 2px;
  border-radius: 10px;
  padding: 10px 12px;
  background: rgba(15, 118, 110, 0.1);
}

.append-tip p {
  margin: 0 0 8px;
  color: #44616b;
  font-size: 0.86rem;
}

.append-sample {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  border-radius: 8px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.84);
  color: #28414a;
  font-size: 0.82rem;
}

.edit-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.foot-right {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.copy-btn,
.ghost-btn,
.save-btn {
  border: 0;
  border-radius: 8px;
  padding: 7px 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  cursor: pointer;
}

.copy-btn {
  color: #3d4f57;
  background: rgba(65, 83, 92, 0.13);
}

.ghost-btn {
  color: #425760;
  background: rgba(65, 83, 92, 0.1);
}

.save-btn {
  color: #effcf6;
  background: linear-gradient(120deg, #0f766e, #0a5f59);
}

.copy-btn:disabled,
.ghost-btn:disabled,
.save-btn:disabled {
  opacity: 0.62;
  cursor: not-allowed;
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

@media (max-width: 1024px) {
  .page-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .upload-card,
  .list-card {
    padding: 12px;
  }

  .edit-modal {
    padding: 12px;
  }

  .edit-textarea {
    min-height: 260px;
  }

  .file-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .edit-foot {
    align-items: stretch;
  }

  .foot-right {
    width: 100%;
    justify-content: flex-end;
  }

  .toast {
    right: 10px;
    left: 10px;
    bottom: 12px;
    justify-content: center;
  }
}
</style>

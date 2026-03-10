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
            <button class="download-btn" @click="downloadFile(item.relative_path)">
              <i class="fa-solid fa-download"></i>
              {{ t('upload.download') }}
            </button>
          </div>
        </li>
      </ul>
    </section>

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

  .toast {
    right: 10px;
    left: 10px;
    bottom: 12px;
    justify-content: center;
  }
}
</style>

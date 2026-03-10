import { ref } from 'vue'

const LOCALE_STORAGE_KEY = 'ui_locale'
const DEFAULT_LOCALE = 'en'
const SUPPORTED_LOCALES = new Set(['en', 'zh'])

const messages = {
  en: {
    common: {
      english: 'English',
      chinese: '中文',
      languageSwitch: 'Language switch'
    },
    app: {
      brandTag: 'Mobile Localization Collaboration',
      title: 'Translation Workspace',
      navUpload: 'File Upload',
      navEditor: 'Trilingual Key Editor',
      logout: 'Logout'
    },
    login: {
      tag: 'Access Control',
      title: 'Sign in to continue',
      description: 'Only authenticated users can open the upload and editor pages.',
      usernameLabel: 'Username',
      usernamePlaceholder: 'Enter username',
      passwordLabel: 'Password',
      passwordPlaceholder: 'Enter password',
      submit: 'Sign In',
      submitting: 'Signing in...',
      errorMissing: 'Please enter username and password.',
      errorFailed: 'Login failed',
      errorSession: 'Login succeeded but session cookie is not ready. Make sure frontend and backend use the same host.'
    },
    upload: {
      sourceTitle: 'Source File Upload',
      uploadedTitle: 'Uploaded Files',
      supportedTip: 'Supported languages: English, Arabic, Turkish. Each upload replaces the existing file under the same platform and language, even with a different filename.',
      dragHint: 'Drag files here, or click the button to select',
      dragHelp: 'iOS supports only .strings, android supports only .xml',
      selectFiles: 'Select Files',
      noFilesSelected: 'No files selected',
      uploading: 'Uploading...',
      uploadReplace: 'Upload & Replace',
      filesCount: '{count} files',
      loadingList: 'Loading file list...',
      emptyList: 'No files for the selected language yet',
      download: 'Download',
      languageEnglish: 'English',
      languageArabic: 'Arabic',
      languageTurkish: 'Turkish',
      toastSelectFile: 'Please select files first',
      toastLoadFileListFailed: 'Failed to load file list',
      toastInvalidFileType: '{name} has an invalid file type: {tip}',
      toastInvalidIosTip: 'iOS supports only .strings files',
      toastInvalidAndroidTip: 'android supports only .xml files',
      toastUploadSuccess: 'Upload successful. Existing file for this platform and language was replaced.',
      toastUploadFailed: 'Upload failed',
      toastDownloadFailed: 'Download failed',
      toastUploadSingleFailed: '{name} upload failed'
    },
    editor: {
      title: 'Trilingual Key Editor',
      uploaded: 'Uploaded',
      notUploaded: 'Not uploaded',
      featureNote: 'Auto-save rule: data is saved only when a field loses focus and content has changed. Non-English edits (Arabic/Turkish) are auto-synced to the other platform when the English value matches.',
      loading: 'Loading editor data...',
      noEditableFile: 'No editable file exists on this platform yet. Please upload at least one source file on the "File Upload" page first.',
      searchByKey: 'Search by key',
      refresh: 'Refresh',
      addKey: 'Add key',
      columnKey: 'Key',
      columnEnglish: 'English',
      columnArabic: 'Arabic',
      columnTurkish: 'Turkish',
      columnActions: 'Actions',
      keyExample: 'e.g. check_my_decoration',
      newTag: 'NEW',
      deleteConfirmTitle: 'Are you sure you want to delete key "{key}"?',
      deleteConfirmBody: 'Deletion will be written into uploaded language files during auto-save.',
      cancel: 'Cancel',
      delete: 'Delete',
      valuePlaceholder: 'Enter translation text',
      valueMissingPlaceholder: 'Source file for this language is not uploaded yet',
      keyEmpty: '(key is empty)',
      toastLoadFailed: 'Failed to load editor data',
      toastSaveFailed: 'Save failed',
      toastSaved: 'Saved successfully',
      hintEnabled: 'Auto-save is enabled',
      hintNoTarget: 'No auto-save target is available',
      hintUnavailable: 'Auto-save is unavailable',
      hintEditing: 'Editing... will auto-save on blur',
      hintNoChanges: 'No changes detected. Skipped save ({time})',
      hintSaving: 'Auto-saving...',
      hintSaved: 'Auto-saved ({time})',
      hintSavedSynced: 'Auto-saved and synced {count} rows to {platform} ({time})',
      hintSaveFailed: 'Auto-save failed. Keep editing to retry automatically.'
    }
  },
  zh: {
    common: {
      english: 'English',
      chinese: '中文',
      languageSwitch: '语言切换'
    },
    app: {
      brandTag: '移动端本地化协作',
      title: '翻译工作台',
      navUpload: '文件上传',
      navEditor: '三语键值编辑',
      logout: '退出登录'
    },
    login: {
      tag: '访问控制',
      title: '登录后继续',
      description: '只有已认证用户可以打开上传页和编辑页。',
      usernameLabel: '用户名',
      usernamePlaceholder: '请输入用户名',
      passwordLabel: '密码',
      passwordPlaceholder: '请输入密码',
      submit: '登录',
      submitting: '登录中...',
      errorMissing: '请输入用户名和密码。',
      errorFailed: '登录失败',
      errorSession: '登录成功但会话未就绪，请确认前后端使用同一主机名。'
    },
    upload: {
      sourceTitle: '源文件上传',
      uploadedTitle: '已上传文件',
      supportedTip: '支持语言：英语、阿拉伯语、土耳其语。相同平台和语种下，上传会覆盖已有文件，即使文件名不同。',
      dragHint: '将文件拖到这里，或点击按钮选择文件',
      dragHelp: 'iOS 仅支持 .strings，android 仅支持 .xml',
      selectFiles: '选择文件',
      noFilesSelected: '未选择文件',
      uploading: '上传中...',
      uploadReplace: '上传并覆盖',
      filesCount: '{count} 个文件',
      loadingList: '正在加载文件列表...',
      emptyList: '当前语种暂无文件',
      download: '下载',
      languageEnglish: '英语',
      languageArabic: '阿拉伯语',
      languageTurkish: '土耳其语',
      toastSelectFile: '请先选择文件',
      toastLoadFileListFailed: '加载文件列表失败',
      toastInvalidFileType: '{name} 文件类型不正确：{tip}',
      toastInvalidIosTip: 'iOS 仅支持 .strings 文件',
      toastInvalidAndroidTip: 'android 仅支持 .xml 文件',
      toastUploadSuccess: '上传成功。该平台与语种下的已有文件已覆盖。',
      toastUploadFailed: '上传失败',
      toastDownloadFailed: '下载失败',
      toastUploadSingleFailed: '{name} 上传失败'
    },
    editor: {
      title: '三语键值编辑器',
      uploaded: '已上传',
      notUploaded: '未上传',
      featureNote: '自动保存规则：仅在输入框失焦且内容有变化时保存。非英文改动（阿语/土耳其语）会在英文值一致时自动同步到另一端。',
      loading: '正在加载编辑数据...',
      noEditableFile: '该平台还没有可编辑文件，请先到“文件上传”页面至少上传一个源文件。',
      searchByKey: '按 key 搜索',
      refresh: '刷新',
      addKey: '新增 key',
      columnKey: '键',
      columnEnglish: '英文',
      columnArabic: '阿语',
      columnTurkish: '土耳其语',
      columnActions: '操作',
      keyExample: '例如 check_my_decoration',
      newTag: 'NEW',
      deleteConfirmTitle: '确定删除 key “{key}” 吗？',
      deleteConfirmBody: '删除后会在自动保存时写回到已上传的语言文件中。',
      cancel: '取消',
      delete: '删除',
      valuePlaceholder: '请输入翻译内容',
      valueMissingPlaceholder: '该语言的源文件尚未上传',
      keyEmpty: '(key 为空)',
      toastLoadFailed: '加载编辑数据失败',
      toastSaveFailed: '保存失败',
      toastSaved: '保存成功',
      hintEnabled: '已启用自动保存',
      hintNoTarget: '当前没有可自动保存的目标文件',
      hintUnavailable: '自动保存不可用',
      hintEditing: '编辑中，失焦后自动保存',
      hintNoChanges: '未检测到变化，已跳过保存（{time}）',
      hintSaving: '自动保存中...',
      hintSaved: '已自动保存（{time}）',
      hintSavedSynced: '已自动保存，并同步 {count} 行到 {platform}（{time}）',
      hintSaveFailed: '自动保存失败，继续编辑会自动重试。'
    }
  }
}

function readInitialLocale() {
  if (typeof window === 'undefined') {
    return DEFAULT_LOCALE
  }
  const saved = window.localStorage.getItem(LOCALE_STORAGE_KEY) || ''
  if (SUPPORTED_LOCALES.has(saved)) {
    return saved
  }
  return DEFAULT_LOCALE
}

const locale = ref(readInitialLocale())

function resolveMessage(table, keyPath) {
  return keyPath.split('.').reduce((current, key) => {
    if (!current || typeof current !== 'object') {
      return undefined
    }
    return Object.prototype.hasOwnProperty.call(current, key) ? current[key] : undefined
  }, table)
}

function formatMessage(template, params) {
  if (typeof template !== 'string') {
    return ''
  }
  return template.replace(/\{(\w+)\}/g, (_, key) => {
    if (Object.prototype.hasOwnProperty.call(params, key)) {
      return String(params[key])
    }
    return `{${key}}`
  })
}

export function useI18n() {
  function setLocale(nextLocale) {
    locale.value = SUPPORTED_LOCALES.has(nextLocale) ? nextLocale : DEFAULT_LOCALE
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, locale.value)
    }
  }

  function t(keyPath, params = {}) {
    const current = resolveMessage(messages[locale.value], keyPath)
    const fallback = resolveMessage(messages[DEFAULT_LOCALE], keyPath)
    const selected = current ?? fallback ?? keyPath
    return formatMessage(selected, params)
  }

  return {
    locale,
    setLocale,
    t
  }
}

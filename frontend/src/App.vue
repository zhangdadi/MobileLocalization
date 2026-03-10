<script setup>
/**
 * File: App.vue
 * Description: Global shell layout, navigation, locale switch, and logout logic.
 * Author: zhangdadi
 * Created: 2026-03-10
 */

import { computed } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useI18n } from './i18n'

const apiBase = import.meta.env.VITE_API_BASE || ''
const route = useRoute()
const router = useRouter()
const { locale, setLocale, t } = useI18n()

const hideShell = computed(() => route.path === '/login')

async function logout() {
  const token = window.localStorage.getItem('auth_token') || ''
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  await fetch(`${apiBase}/api/auth/logout`, {
    method: 'POST',
    credentials: 'include',
    headers
  }).catch(() => {})
  window.localStorage.removeItem('auth_token')
  await router.replace('/login')
}
</script>

<template>
  <div class="app-shell">
    <header v-if="!hideShell" class="topbar">
      <div class="brand-block">
        <p class="brand-tag">{{ t('app.brandTag') }}</p>
        <h1>{{ t('app.title') }}</h1>
      </div>
      <nav class="nav-tabs">
        <RouterLink to="/upload" class="tab">{{ t('app.navUpload') }}</RouterLink>
        <RouterLink to="/editor" class="tab">{{ t('app.navEditor') }}</RouterLink>
        <div class="locale-switch" :aria-label="t('common.languageSwitch')">
          <button :class="{ active: locale === 'en' }" @click="setLocale('en')">{{ t('common.english') }}</button>
          <button :class="{ active: locale === 'zh' }" @click="setLocale('zh')">{{ t('common.chinese') }}</button>
        </div>
        <button class="logout-btn" @click="logout">
          <i class="fa-solid fa-right-from-bracket"></i>
          {{ t('app.logout') }}
        </button>
      </nav>
    </header>

    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  padding: 18px 18px 24px;
}

.topbar {
  width: min(1380px, 96vw);
  margin: 0 auto;
  padding: 18px;
  border: 1px solid rgba(15, 118, 110, 0.25);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(6px);
  box-shadow: 0 14px 24px rgba(18, 32, 38, 0.12);
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.brand-tag {
  margin: 0;
  color: #0f766e;
  font-weight: 700;
  font-size: 0.88rem;
}

.brand-block h1 {
  margin: 4px 0 0;
  font-family: 'Noto Serif SC', serif;
  font-size: clamp(1.35rem, 2.2vw, 1.8rem);
}

.nav-tabs {
  display: inline-flex;
  gap: 10px;
  flex-wrap: wrap;
}

.tab {
  text-decoration: none;
  padding: 9px 16px;
  border-radius: 999px;
  color: #405560;
  font-weight: 700;
  background: #e5efed;
  transition: all 0.2s ease;
}

.tab.router-link-active {
  color: #e9fffc;
  background: linear-gradient(120deg, #0f766e, #0b5f59);
}

.locale-switch {
  display: inline-flex;
  border-radius: 999px;
  padding: 2px;
  background: #d5e4e0;
}

.locale-switch button {
  border: 0;
  padding: 7px 12px;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 700;
  color: #45606b;
  background: transparent;
  cursor: pointer;
}

.locale-switch button.active {
  background: #0f766e;
  color: #e9fffc;
}

.logout-btn {
  border: 0;
  padding: 9px 14px;
  border-radius: 999px;
  color: #fff6ef;
  background: linear-gradient(120deg, #d9480f, #b53a0c);
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.main-content {
  width: min(1380px, 96vw);
  margin: 14px auto 0;
}

@media (max-width: 640px) {
  .app-shell {
    padding: 12px 10px 18px;
  }

  .topbar,
  .main-content {
    width: 100%;
  }

  .topbar {
    padding: 14px;
  }
}
</style>

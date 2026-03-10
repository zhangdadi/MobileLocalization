<script setup>
/**
 * File: LoginPage.vue
 * Description: Login page with credential submission and session validation.
 * Author: zhangdadi
 * Created: 2026-03-10
 */

import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '../i18n'

const apiBase = import.meta.env.VITE_API_BASE || ''

const route = useRoute()
const router = useRouter()
const { locale, setLocale, t } = useI18n()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

async function waitForSessionReady(token = '', maxRetry = 8, delayMs = 120) {
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  for (let i = 0; i < maxRetry; i += 1) {
    try {
      const response = await fetch(`${apiBase}/api/auth/me`, {
        credentials: 'include',
        headers
      })
      if (response.ok) {
        return true
      }
    } catch {
      // no-op
    }

    await new Promise((resolve) => {
      window.setTimeout(resolve, delayMs)
    })
  }

  return false
}

async function submitLogin() {
  if (!username.value.trim() || !password.value) {
    errorMessage.value = t('login.errorMissing')
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const response = await fetch(`${apiBase}/api/auth/login`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: username.value.trim(),
        password: password.value
      })
    })

    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data.detail || t('login.errorFailed'))
    }

    const token = typeof data.access_token === 'string' ? data.access_token : ''
    if (token) {
      window.localStorage.setItem('auth_token', token)
    } else {
      window.localStorage.removeItem('auth_token')
    }

    const sessionReady = await waitForSessionReady(token)
    if (!sessionReady) {
      throw new Error(t('login.errorSession'))
    }

    const redirectTarget = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
      ? route.query.redirect
      : '/upload'
    await router.replace(redirectTarget)
  } catch (error) {
    errorMessage.value = error.message || t('login.errorFailed')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="login-wrap">
    <div class="login-card">
      <div class="locale-row">
        <p class="tag">{{ t('login.tag') }}</p>
        <div class="locale-switch" :aria-label="t('common.languageSwitch')">
          <button :class="{ active: locale === 'en' }" @click="setLocale('en')">{{ t('common.english') }}</button>
          <button :class="{ active: locale === 'zh' }" @click="setLocale('zh')">{{ t('common.chinese') }}</button>
        </div>
      </div>
      <h2>{{ t('login.title') }}</h2>
      <p class="desc">{{ t('login.description') }}</p>

      <label class="field-label" for="login-username">{{ t('login.usernameLabel') }}</label>
      <input
        id="login-username"
        v-model="username"
        class="field"
        type="text"
        autocomplete="username"
        :placeholder="t('login.usernamePlaceholder')"
        @keydown.enter="submitLogin"
      />

      <label class="field-label" for="login-password">{{ t('login.passwordLabel') }}</label>
      <input
        id="login-password"
        v-model="password"
        class="field"
        type="password"
        autocomplete="current-password"
        :placeholder="t('login.passwordPlaceholder')"
        @keydown.enter="submitLogin"
      />

      <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

      <button class="submit-btn" :disabled="loading" @click="submitLogin">
        <i class="fa-solid fa-right-to-bracket"></i>
        {{ loading ? t('login.submitting') : t('login.submit') }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.login-wrap {
  min-height: calc(100vh - 140px);
  display: grid;
  place-items: center;
  padding: 10px;
}

.login-card {
  width: min(440px, 94vw);
  border-radius: 18px;
  border: 1px solid rgba(15, 118, 110, 0.24);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 16px 26px rgba(18, 32, 38, 0.14);
  padding: 20px;
}

.locale-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.tag {
  margin: 0;
  color: #0f766e;
  font-weight: 700;
  font-size: 0.86rem;
}

.locale-switch {
  display: inline-flex;
  border-radius: 999px;
  padding: 2px;
  background: #d5e4e0;
}

.locale-switch button {
  border: 0;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 0.82rem;
  font-weight: 700;
  color: #45606b;
  background: transparent;
  cursor: pointer;
}

.locale-switch button.active {
  color: #ecfffc;
  background: #0f766e;
}

h2 {
  margin: 6px 0 0;
  color: #15252c;
  font-size: 1.3rem;
}

.desc {
  margin: 8px 0 0;
  color: #55707a;
  font-size: 0.92rem;
  line-height: 1.6;
}

.field-label {
  margin-top: 14px;
  display: block;
  color: #35505a;
  font-size: 0.88rem;
  font-weight: 700;
}

.field {
  margin-top: 6px;
  width: 100%;
  border: 1px solid rgba(65, 83, 92, 0.24);
  border-radius: 10px;
  background: #fbfefe;
  color: #132126;
  padding: 10px;
  outline: none;
}

.field:focus {
  border-color: rgba(15, 118, 110, 0.72);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.16);
}

.error-text {
  margin: 10px 0 0;
  color: #b93f15;
  font-size: 0.9rem;
}

.submit-btn {
  margin-top: 14px;
  width: 100%;
  border: 0;
  border-radius: 10px;
  padding: 10px 14px;
  display: inline-flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: #ecfffc;
  background: linear-gradient(120deg, #0f766e, #0b5f59);
  cursor: pointer;
}

.submit-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
</style>

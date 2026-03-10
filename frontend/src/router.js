import { createRouter, createWebHistory } from 'vue-router'
import UploadPage from './pages/UploadPage.vue'
import EditorPage from './pages/EditorPage.vue'
import LoginPage from './pages/LoginPage.vue'

const apiBase = import.meta.env.VITE_API_BASE || ''

function getAuthHeaders() {
  const token = window.localStorage.getItem('auth_token') || ''
  if (!token) {
    return {}
  }
  return {
    Authorization: `Bearer ${token}`
  }
}

async function isAuthenticated() {
  try {
    const response = await fetch(`${apiBase}/api/auth/me`, {
      credentials: 'include',
      headers: getAuthHeaders()
    })
    if (!response.ok && window.localStorage.getItem('auth_token')) {
      window.localStorage.removeItem('auth_token')
    }
    return response.ok
  } catch {
    return false
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/upload',
      meta: { requiresAuth: true }
    },
    {
      path: '/login',
      component: LoginPage,
      meta: { public: true }
    },
    {
      path: '/upload',
      component: UploadPage,
      meta: { requiresAuth: true }
    },
    {
      path: '/editor',
      component: EditorPage,
      meta: { requiresAuth: true }
    }
  ]
})

router.beforeEach(async (to) => {
  if (to.meta.public) {
    if (to.path === '/login' && (await isAuthenticated())) {
      return { path: '/upload' }
    }
    return true
  }

  if (await isAuthenticated()) {
    return true
  }

  return {
    path: '/login',
    query: { redirect: to.fullPath }
  }
})

export default router

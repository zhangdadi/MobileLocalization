/**
 * File: main.js
 * Description: Frontend app bootstrap entry.
 * Author: zhangdadi
 * Created: 2026-03-10
 */

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import '@fontsource/noto-sans-sc/400.css'
import '@fontsource/noto-sans-sc/500.css'
import '@fontsource/noto-sans-sc/700.css'
import '@fontsource/noto-sans-sc/900.css'
import '@fontsource/noto-serif-sc/700.css'
import '@fontsource/noto-serif-sc/900.css'
import './style.css'

createApp(App).use(router).mount('#app')

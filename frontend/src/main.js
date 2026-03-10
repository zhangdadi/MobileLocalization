/**
 * File: main.js
 * Description: Frontend app bootstrap entry.
 * Author: zhangdadi
 * Created: 2026-03-10
 */

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

createApp(App).use(router).mount('#app')

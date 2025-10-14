import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import SearchPage from './views/SearchPage.vue'
import VersionHistory from './views/VersionHistory.vue'
import DiffView from './views/DiffView.vue'
import JarUnifiedDiff from './views/JarUnifiedDiff.vue'

const routes = [
  { path: '/', component: SearchPage },
  { path: '/history/:type/:name', component: VersionHistory },
  { path: '/diff/:type/:name/:fromVersion/:toVersion', component: DiffView },
  { path: '/diff-unified/jar/:name/:fromVersion/:toVersion', component: JarUnifiedDiff }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const app = createApp(App)

// 注册Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus)
app.use(router)
app.mount('#app')

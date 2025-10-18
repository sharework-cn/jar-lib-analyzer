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
import JarFileDiff from './views/JarFileDiff.vue'
import ServicesPage from './views/ServicesPage.vue'
import ServiceDetailPage from './views/ServiceDetailPage.vue'
import JarSourcesPage from './views/JarSourcesPage.vue'
import JarsPage from './views/JarsPage.vue'
import JavaSourcesPage from './views/JavaSourcesPage.vue'
import JavaSourceDetailsPage from './views/JavaSourceDetailsPage.vue'

const routes = [
  { path: '/', component: SearchPage },
  { path: '/services', component: ServicesPage },
  { path: '/services/:id', component: ServiceDetailPage },
  { path: '/jars', component: JarsPage },
  { path: '/java-sources', component: JavaSourcesPage },
  { path: '/java-source-details/:classFullName', component: JavaSourceDetailsPage },
  { path: '/history/:type/:name', component: VersionHistory },
  { path: '/jar-sources/:jarName/:versionNo', component: JarSourcesPage },
  { path: '/diff/:type/:name/:fromVersion/:toVersion', component: DiffView },
  { path: '/diff/jar-file/:jarName/:fromVersion/:toVersion', component: JarFileDiff },
  { path: '/diff/class-file/:className/:fromVersion/:toVersion', component: JarFileDiff },
  { path: '/diff-unified/:type/:name/:fromVersion/:toVersion', component: JarUnifiedDiff }
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

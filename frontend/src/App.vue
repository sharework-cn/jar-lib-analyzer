<template>
  <div id="app">
    <el-container>
      <el-header class="app-header">
        <div class="header-content">
          <h1 class="app-title">
            <el-icon class="title-icon"><Search /></el-icon>
            Java库分析系统
          </h1>
          <div class="header-actions">
            <el-breadcrumb separator="/" v-if="showBreadcrumb">
              <el-breadcrumb-item 
                v-for="item in breadcrumbItems" 
                :key="item.path"
                :to="item.path"
              >
                {{ item.title }}
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Search } from '@element-plus/icons-vue'

const route = useRoute()

const showBreadcrumb = computed(() => {
  return route.path !== '/'
})

const breadcrumbItems = computed(() => {
  const items = [{ title: '搜索', path: '/' }]
  
  if (route.path.startsWith('/history/')) {
    const [, , type, name] = route.path.split('/')
    items.push({ title: `${type === 'jar' ? 'JAR' : 'Class'}: ${name}`, path: route.path })
  } else if (route.path.startsWith('/diff/')) {
    const [, , type, name, fromVersion, toVersion] = route.path.split('/')
    items.push(
      { title: `${type === 'jar' ? 'JAR' : 'Class'}: ${name}`, path: `/history/${type}/${name}` },
      { title: `版本 ${fromVersion} → ${toVersion}`, path: route.path }
    )
  }
  
  return items
})
</script>

<style scoped>
.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 0;
  height: 80px !important;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  padding: 0 2rem;
}

.app-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.title-icon {
  font-size: 1.8rem;
}

.app-main {
  padding: 2rem;
  min-height: calc(100vh - 80px);
}

:deep(.el-breadcrumb__inner) {
  color: rgba(255, 255, 255, 0.8) !important;
}

:deep(.el-breadcrumb__inner.is-link) {
  color: white !important;
}

:deep(.el-breadcrumb__inner.is-link:hover) {
  color: #e6f7ff !important;
}
</style>

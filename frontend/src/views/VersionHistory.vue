<template>
  <div class="version-history">
    <div class="history-header">
      <h2>{{ itemTitle }}</h2>
      <p class="item-subtitle">{{ itemType === 'jar' ? 'JAR文件' : 'Class文件' }}版本历史</p>
    </div>

    <div class="version-timeline" v-if="versions.length > 0">
      <div 
        v-for="(version, index) in versions" 
        :key="version.version_no"
        class="version-item"
      >
        <div class="version-marker">
          <div class="version-number">{{ version.version_no }}</div>
        </div>
        
        <div class="version-content">
          <div class="version-header">
            <div class="version-info">
              <h3 class="version-title">版本 {{ version.version_no }}</h3>
              <div class="version-meta">
                <el-tag size="small" type="info">{{ formatFileSize(version.file_size) }}</el-tag>
                <span class="version-count">{{ version.file_count }}个文件</span>
                <el-tag v-if="version.source_hash" size="small" type="success" class="source-hash-tag">
                  <el-icon><Key /></el-icon>
                  {{ version.source_hash.substring(0, 8) }}...
                </el-tag>
              </div>
            </div>
            <div class="version-actions">
              <el-button 
                v-if="index > 0" 
                type="primary" 
                size="small"
                @click="goToDiff(version.version_no, versions[index-1].version_no)"
              >
                <el-icon><Switch /></el-icon>
                查看差异
              </el-button>
              <el-button 
                v-if="index > 0" 
                size="small"
                @click="goToUnifiedDiff(version.version_no, versions[index-1].version_no)"
              >
                <el-icon><Switch /></el-icon>
                GitHub风格（单窗格）
              </el-button>
              <el-button size="small" @click="viewSources(version.version_no)">
                <el-icon><View /></el-icon>
                查看源码
              </el-button>
            </div>
          </div>
          
          <div class="version-details">
            <div class="time-range">
              <el-icon><Clock /></el-icon>
              <span>{{ formatTimeRange(version.earliest_time, version.latest_time) }}</span>
            </div>
            
            <div class="services-section">
              <div class="services-header">
                <el-icon><OfficeBuilding /></el-icon>
                <span>使用该版本的服务 ({{ version.service_count }}个)</span>
              </div>
              <div class="services-list">
                <el-tag 
                  v-for="service in version.services" 
                  :key="service"
                  size="small"
                  class="service-tag"
                >
                  {{ service }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="loading-container" v-if="loading">
      <el-skeleton :rows="5" animated />
    </div>

    <div class="no-versions" v-if="!loading && versions.length === 0">
      <el-empty description="暂无版本数据" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Clock, OfficeBuilding, Switch, View, Key } from '@element-plus/icons-vue'
import { getVersionHistory } from '@/api/versions'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(true)
const versions = ref([])

// 计算属性
const itemType = computed(() => route.params.type)
const itemName = computed(() => decodeURIComponent(route.params.name))
const itemTitle = computed(() => `${itemName.value} 版本历史`)

// 方法
const loadVersionHistory = async () => {
  loading.value = true
  try {
    const data = await getVersionHistory(itemType.value, itemName.value)
    versions.value = data.versions
  } catch (error) {
    console.error('加载版本历史失败:', error)
    ElMessage.error('加载版本历史失败')
  } finally {
    loading.value = false
  }
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const formatTimeRange = (earliest, latest) => {
  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString('zh-CN')
  }
  
  if (earliest === latest) {
    return formatDate(earliest)
  }
  
  return `${formatDate(earliest)} ~ ${formatDate(latest)}`
}

const goToDiff = (fromVersion, toVersion) => {
  router.push(`/diff/${itemType.value}/${encodeURIComponent(itemName.value)}/${fromVersion}/${toVersion}`)
}

const goToUnifiedDiff = (fromVersion, toVersion) => {
  router.push(`/diff-unified/${itemType.value}/${encodeURIComponent(itemName.value)}/${fromVersion}/${toVersion}`)
}

const viewSources = (versionNo) => {
  // 查看源码功能
  ElMessage.info(`查看版本 ${versionNo} 的源码`)
}

// 生命周期
onMounted(() => {
  loadVersionHistory()
})
</script>

<style scoped>
.version-history {
  max-width: 1000px;
  margin: 0 auto;
}

.history-header {
  margin-bottom: 2rem;
}

.history-header h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.8rem;
  color: #212529;
}

.item-subtitle {
  color: #6c757d;
  margin: 0;
}

.version-timeline {
  position: relative;
  padding-left: 3rem;
}

.version-timeline::before {
  content: '';
  position: absolute;
  left: 1.5rem;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #dee2e6;
}

.version-item {
  position: relative;
  margin-bottom: 2rem;
}

.version-marker {
  position: absolute;
  left: -3rem;
  top: 0;
  width: 3rem;
  height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.version-number {
  width: 2rem;
  height: 2rem;
  background: #007bff;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.875rem;
  box-shadow: 0 0 0 3px white, 0 0 0 6px #dee2e6;
}

.version-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 1.5rem;
  border-left: 4px solid #007bff;
}

.version-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.version-title {
  margin: 0 0 0.5rem 0;
  font-size: 1.2rem;
  color: #212529;
}

.version-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.source-hash-tag {
  font-family: ui-monospace, SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 11px;
}

.version-count {
  font-size: 0.875rem;
  color: #6c757d;
}

.version-actions {
  display: flex;
  gap: 0.5rem;
}

.version-details {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.time-range {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #6c757d;
  font-size: 0.875rem;
}

.services-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.services-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  color: #495057;
}

.services-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.service-tag {
  margin: 0;
}

.loading-container {
  padding: 2rem;
}

.no-versions {
  text-align: center;
  padding: 3rem 0;
}
</style>

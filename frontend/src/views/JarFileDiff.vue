<template>
  <div class="jar-file-diff">
    <div class="diff-header">
      <div class="header-content">
        <el-button 
          type="primary" 
          :icon="ArrowLeft" 
          @click="goBack"
          class="back-button"
        >
          返回文件列表
        </el-button>
        <div class="title-info">
          <h2>{{ diffTitle }}</h2>
          <div class="file-path">
            <el-icon><Document /></el-icon>
            <span>{{ filePath }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 差异内容 -->
    <div class="diff-content" v-if="!loading && fileData">
      <DiffViewer
        :file-path="filePath"
        :from-version="fromVersion"
        :to-version="toVersion"
        :from-content="fileData.fromContent"
        :to-content="fileData.toContent"
        :additions="fileStats.additions"
        :deletions="fileStats.deletions"
        :change-percentage="fileStats.change_percentage"
        :size-before="fileStats.size_before"
        :size-after="fileStats.size_after"
      />
    </div>

    <!-- 加载状态 -->
    <div class="loading-container" v-if="loading">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- 无差异 -->
    <div class="no-diff" v-if="!loading && !fileData">
      <el-empty description="该文件在两个版本之间没有差异" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Document } from '@element-plus/icons-vue'
import { getVersionDiff } from '@/api/diff'
import DiffViewer from '@/components/DiffViewer.vue'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(true)
const fileData = ref(null)
const fileStats = ref({})

// 计算属性
const jarName = computed(() => decodeURIComponent(route.params.jarName))
const fromVersion = computed(() => parseInt(route.params.fromVersion))
const toVersion = computed(() => parseInt(route.params.toVersion))
const filePath = computed(() => decodeURIComponent(route.params.filePath))

const diffTitle = computed(() => {
  return `${jarName.value} 版本 ${fromVersion.value} → ${toVersion.value} 差异对比`
})

// 方法
const loadFileDiff = async () => {
  loading.value = true
  try {
    console.log('Loading JAR file diff:', jarName.value, fromVersion.value, toVersion.value, filePath.value)
    
    // 获取文件差异数据
    const diff = await getVersionDiff('jar', jarName.value, fromVersion.value, toVersion.value, filePath.value)
    
    // 获取文件内容
    const fromContent = diff.from_content || ''
    const toContent = diff.to_content || ''
    
    fileData.value = {
      fromContent,
      toContent
    }
    
    // 获取文件统计信息（从文件变更列表中查找）
    const summaryData = await getVersionDiff('jar', jarName.value, fromVersion.value, toVersion.value)
    const fileChange = summaryData.file_changes?.find(f => f.file_path === filePath.value)
    
    if (fileChange) {
      fileStats.value = {
        additions: fileChange.additions || 0,
        deletions: fileChange.deletions || 0,
        change_percentage: fileChange.change_percentage || 0,
        size_before: fileChange.size_before || 0,
        size_after: fileChange.size_after || 0
      }
    }
    
  } catch (error) {
    console.error('加载JAR文件差异失败:', error)
    ElMessage.error('加载文件差异失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push(`/diff/jar/${encodeURIComponent(jarName.value)}/${fromVersion.value}/${toVersion.value}`)
}

// 生命周期
onMounted(() => {
  loadFileDiff()
})
</script>

<style scoped>
.jar-file-diff {
  width: 100%;
  max-width: 100%;
  padding: 0 1rem;
  box-sizing: border-box;
}

.diff-header {
  margin-bottom: 2rem;
  padding: 1rem 0;
  border-bottom: 1px solid #e1e4e8;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.back-button {
  flex-shrink: 0;
}

.title-info {
  flex: 1;
  min-width: 0;
}

.title-info h2 {
  margin: 0 0 0.5rem 0;
  color: #24292f;
  font-size: 1.5rem;
  font-weight: 600;
}

.file-path {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #656d76;
  font-size: 0.875rem;
}

.file-path .el-icon {
  color: #656d76;
}

.diff-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}

.loading-container {
  padding: 2rem;
}

.no-diff {
  padding: 4rem 2rem;
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .jar-file-diff {
    padding: 0 0.5rem;
  }
  
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .title-info h2 {
    font-size: 1.25rem;
  }
}
</style>

<template>
  <div class="diff-view">
    <div class="diff-header">
      <h2>{{ diffTitle }}</h2>
      <div class="header-controls">
        <div class="diff-summary" v-if="diffSummary">
          <el-tag type="success">+{{ diffSummary.insertions }}</el-tag>
          <el-tag type="danger">-{{ diffSummary.deletions }}</el-tag>
          <span class="summary-text">
            {{ diffSummary.files_changed }}个文件变更，共{{ fileChanges.length }}个文件
          </span>
        </div>
        <div class="view-toggle">
          <el-button-group>
            <el-button 
              :type="viewMode === 'dual' ? 'primary' : ''"
              @click="setViewMode('dual')"
              size="small"
            >
              双窗格
            </el-button>
            <el-button 
              :type="viewMode === 'unified' ? 'primary' : ''"
              @click="setViewMode('unified')"
              size="small"
            >
              单窗格
            </el-button>
          </el-button-group>
        </div>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content" v-if="fileChanges.length > 0">
      <!-- 文件列表 -->
      <div class="file-list">
        <h3>文件变更</h3>
        <div class="file-tree">
          <div 
            v-for="file in fileChanges" 
            :key="file.file_path"
            class="file-item"
            :class="{ active: selectedFile === file.file_path }"
            @click="selectFile(file.file_path)"
          >
            <div class="file-info">
              <el-icon class="file-icon"><Document /></el-icon>
              <span class="file-name">{{ file.file_path }}</span>
            </div>
            <div class="file-stats">
              <el-tag size="small" type="success">+{{ file.additions }}</el-tag>
              <el-tag size="small" type="danger">-{{ file.deletions }}</el-tag>
              <div class="change-bar">
                <div 
                  class="change-indicator"
                  :style="{ width: `${file.change_percentage}%` }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 差异内容 -->
      <div class="diff-content" v-if="selectedFile && currentFileData && itemType !== 'jar'">
        <!-- 双窗格视图 -->
        <DiffViewer
          v-if="viewMode === 'dual'"
          :file-path="selectedFile"
          :from-version="fromVersion"
          :to-version="toVersion"
          :from-content="currentFileData.fromContent"
          :to-content="currentFileData.toContent"
          :additions="currentFileStats.additions"
          :deletions="currentFileStats.deletions"
          :change-percentage="currentFileStats.change_percentage"
          :size-before="currentFileStats.size_before"
          :size-after="currentFileStats.size_after"
          :item-type="itemType"
          :item-name="itemName"
        />
        <!-- 单窗格视图 -->
        <GitHubDiffViewer
          v-else-if="viewMode === 'unified'"
          :file-path="selectedFile"
          :from-version="fromVersion"
          :to-version="toVersion"
          :from-content="currentFileData.fromContent"
          :to-content="currentFileData.toContent"
          :additions="currentFileStats.additions"
          :deletions="currentFileStats.deletions"
          :change-percentage="currentFileStats.change_percentage"
          :size-before="currentFileStats.size_before"
          :size-after="currentFileStats.size_after"
          :item-type="itemType"
          :item-name="itemName"
        />
      </div>
      
      <!-- JAR文件提示 -->
      <div class="jar-hint" v-if="itemType === 'jar' && fileChanges.length > 0">
        <el-alert
          title="点击上方文件查看具体差异"
          type="info"
          :closable="false"
          show-icon
        >
          <template #default>
            选择要查看差异的源码文件，系统将跳转到双窗格差异显示页面。
          </template>
        </el-alert>
      </div>
    </div>

    <!-- 加载状态 -->
    <div class="loading-container" v-if="loading">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- 无差异 -->
    <div class="no-diff" v-if="!loading && fileChanges.length === 0">
      <el-empty description="两个版本之间没有差异" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Document } from '@element-plus/icons-vue'
import { getVersionDiff } from '@/api/diff'
import DiffViewer from '@/components/DiffViewer.vue'
import GitHubDiffViewer from '@/components/GitHubDiffViewer.vue'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(true)
const fileChanges = ref([])
const fileDiffs = ref({})
const fileContents = ref({})
const selectedFile = ref('')
const diffSummary = ref(null)
const viewMode = ref('dual') // 'dual' 或 'unified'

// 计算属性
const itemType = computed(() => route.params.type)
const itemName = computed(() => decodeURIComponent(route.params.name))
const fromVersion = computed(() => parseInt(route.params.fromVersion))
const toVersion = computed(() => parseInt(route.params.toVersion))

const diffTitle = computed(() => {
  return `${itemName.value} 版本 ${fromVersion.value} → ${toVersion.value} 差异对比`
})

const fileDiff = computed(() => {
  return fileDiffs.value[selectedFile.value] || null
})

const currentFileData = computed(() => {
  return fileContents.value[selectedFile.value] || null
})

const currentFileStats = computed(() => {
  const file = fileChanges.value.find(f => f.file_path === selectedFile.value)
  return file || { additions: 0, deletions: 0, change_percentage: 0 }
})

// 方法
const loadDiff = async () => {
  loading.value = true
  try {
    console.log('Loading diff for:', itemType.value, itemName.value, fromVersion.value, toVersion.value)
    const data = await getVersionDiff(itemType.value, itemName.value, fromVersion.value, toVersion.value)
    console.log('Diff data received:', data)
    
    fileChanges.value = data.file_changes || []
    diffSummary.value = data.summary
    
    // 默认选择第一个文件（仅对Class文件）
    if (fileChanges.value.length > 0 && itemType.value !== 'jar') {
      selectedFile.value = fileChanges.value[0].file_path
      await loadFileDiff(selectedFile.value)
    }
  } catch (error) {
    console.error('加载差异数据失败:', error)
    ElMessage.error('加载差异数据失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const loadFileDiff = async (filePath) => {
  if (fileContents.value[filePath]) {
    return // 已缓存
  }
  
  try {
    const diff = await getVersionDiff(itemType.value, itemName.value, fromVersion.value, toVersion.value, filePath)
    
    // 获取文件内容
    const fromContent = diff.from_content || ''
    const toContent = diff.to_content || ''
    
    fileContents.value[filePath] = {
      fromContent,
      toContent
    }
  } catch (error) {
    console.error('加载文件差异失败:', error)
    ElMessage.error(`加载文件 ${filePath} 失败`)
  }
}

const selectFile = async (filePath) => {
  // 如果是JAR文件，跳转到新的差异页面
  if (itemType.value === 'jar') {
    router.push(`/diff/jar-file/${encodeURIComponent(itemName.value)}/${fromVersion.value}/${toVersion.value}/${encodeURIComponent(filePath)}`)
    return
  }
  
  // Class文件保持原有逻辑
  selectedFile.value = filePath
  await loadFileDiff(filePath)
}

const setViewMode = (mode) => {
  if (mode === 'unified') {
    // 跳转到单窗格页面
    router.push(`/diff-unified/${itemType.value}/${encodeURIComponent(itemName.value)}/${fromVersion.value}/${toVersion.value}`)
  } else {
    // 保持在当前页面，切换到双窗格
    viewMode.value = mode
  }
}

const getLineClass = (type) => {
  return {
    'line-added': type === 'added',
    'line-removed': type === 'removed',
    'line-context': type === 'context'
  }
}

const getLinePrefix = (type) => {
  switch (type) {
    case 'added': return '+'
    case 'removed': return '-'
    case 'context': return ' '
    default: return ' '
  }
}

// 生命周期
onMounted(() => {
  loadDiff()
})

// 监听路由变化
watch(() => route.params, () => {
  loadDiff()
}, { deep: true })
</script>

<style scoped>
.diff-view {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
  padding: 0 1rem;
  box-sizing: border-box;
}

.diff-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #dee2e6;
}

.diff-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #212529;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.diff-summary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.view-toggle {
  display: flex;
  align-items: center;
}

.summary-text {
  color: #6c757d;
  font-size: 0.875rem;
}

.file-list {
  margin-bottom: 2rem;
}

.file-list h3 {
  margin-bottom: 1rem;
  color: #495057;
}

.file-tree {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
  width: 100%;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #f1f3f4;
  cursor: pointer;
  transition: background-color 0.2s;
  min-width: 0; /* 允许收缩 */
}

.file-item:hover {
  background: #f8f9fa;
}

.file-item.active {
  background: #e3f2fd;
  border-left: 4px solid #2196f3;
}

.file-item:last-child {
  border-bottom: none;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0; /* 允许收缩 */
  overflow: hidden;
}

.file-icon {
  color: #6c757d;
}

.file-name {
  font-family: monospace;
  font-size: 0.875rem;
  color: #212529;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.file-stats {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0; /* 防止统计信息被压缩 */
}

.diff-content {
  width: 100%;
}

.jar-hint {
  margin-top: 2rem;
  padding: 1rem;
}

.change-bar {
  width: 60px;
  height: 4px;
  background: #e1e4e8;
  border-radius: 2px;
  overflow: hidden;
}

.change-indicator {
  height: 100%;
  background: linear-gradient(90deg, #cf222e 0%, #2da44e 100%);
  transition: width 0.3s ease;
}


.diff-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}

.diff-file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #f6f8fa;
  border-bottom: 1px solid #d0d7de;
}

.diff-file-header h4 {
  margin: 0;
  font-family: monospace;
  color: #212529;
}

.diff-hunks {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.4;
}

.diff-hunk {
  border-bottom: 1px solid #f1f3f4;
}

.diff-hunk:last-child {
  border-bottom: none;
}

.hunk-header {
  background: #f1f8ff;
  color: #0969da;
  padding: 8px 16px;
  font-family: monospace;
  border-left: 4px solid #0969da;
}

.hunk-content {
  background: white;
}

.diff-line {
  display: flex;
  padding: 0;
}

.line-numbers {
  display: flex;
  width: 80px;
  flex-shrink: 0;
}

.old-line-number,
.new-line-number {
  width: 40px;
  text-align: right;
  padding: 0 8px;
  color: #656d76;
  user-select: none;
  font-size: 12px;
}

.line-content {
  flex: 1;
  display: flex;
  padding-left: 8px;
}

.line-prefix {
  width: 20px;
  text-align: center;
  user-select: none;
  font-weight: bold;
}

.line-text {
  flex: 1;
  padding-right: 16px;
}

.line-added {
  background: #ccfdf4;
}

.line-added .old-line-number,
.line-added .new-line-number {
  background: #ccfdf4;
  color: #2da44e;
}

.line-removed {
  background: #ffebe9;
}

.line-removed .old-line-number,
.line-removed .new-line-number {
  background: #ffebe9;
  color: #cf222e;
}

.line-context {
  background: white;
}

.loading-container {
  padding: 2rem;
}

.no-diff {
  text-align: center;
  padding: 3rem 0;
}
</style>

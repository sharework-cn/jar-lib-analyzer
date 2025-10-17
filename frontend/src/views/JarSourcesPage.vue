<template>
  <div class="jar-sources-page">
    <div class="page-header">
      <el-button 
        type="primary" 
        :icon="ArrowLeft" 
        @click="goBack"
        class="back-button"
      >
        Back to Version History
      </el-button>
      <div class="header-info">
        <h2>{{ jarName }} - Version {{ versionNo }} Source Files</h2>
        <p class="page-meta">
          <el-icon><Files /></el-icon>
          {{ sourceFiles.length }} source files
        </p>
      </div>
    </div>

    <!-- Loading State -->
    <div class="loading-container" v-if="loading">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- Source Files List -->
    <div class="sources-container" v-if="!loading && sourceFiles.length > 0">
      <div class="sources-table">
        <el-table :data="sourceFiles" stripe>
          <el-table-column prop="file_path" label="File Path" min-width="300">
            <template #default="{ row }">
              <el-button 
                type="primary" 
                link 
                @click="viewSourceFile(row)"
              >
                {{ row.file_path }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column prop="file_size" label="Size" width="120" align="right">
            <template #default="{ row }">
              {{ formatFileSize(row.file_size) }}
            </template>
          </el-table-column>
          <el-table-column prop="line_count" label="Lines" width="100" align="center" />
          <el-table-column prop="last_modified" label="Last Modified" width="180">
            <template #default="{ row }">
              {{ formatDate(row.last_modified) }}
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Empty State -->
    <div class="empty-state" v-if="!loading && sourceFiles.length === 0">
      <el-empty description="No source files found for this version" />
    </div>

    <!-- Source File Viewer Dialog -->
    <el-dialog
      v-model="sourceDialogVisible"
      :title="selectedFile?.file_path"
      width="80%"
      :before-close="closeSourceDialog"
    >
      <div class="source-viewer" v-if="selectedFile">
        <div class="source-header">
          <div class="file-info">
            <el-tag type="info">{{ formatFileSize(selectedFile.file_size) }}</el-tag>
            <el-tag type="success">{{ selectedFile.line_count }} lines</el-tag>
            <span class="last-modified">{{ formatDate(selectedFile.last_modified) }}</span>
          </div>
        </div>
        <div class="source-content">
          <pre><code>{{ selectedFileContent }}</code></pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Files } from '@element-plus/icons-vue'
import { getJarSourceFiles, getJarSourceFileContent } from '@/api/jar-sources'

const route = useRoute()
const router = useRouter()

// Reactive data
const loading = ref(true)
const sourceFiles = ref([])
const sourceDialogVisible = ref(false)
const selectedFile = ref(null)
const selectedFileContent = ref('')

// Computed properties
const jarName = computed(() => decodeURIComponent(route.params.jarName))
const versionNo = computed(() => parseInt(route.params.versionNo))

// Methods
const loadSourceFiles = async () => {
  loading.value = true
  try {
    const data = await getJarSourceFiles(jarName.value, versionNo.value)
    sourceFiles.value = data
  } catch (error) {
    console.error('Failed to load source files:', error)
    ElMessage.error('Failed to load source files')
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push(`/history/jar/${encodeURIComponent(jarName.value)}`)
}

const viewSourceFile = async (file) => {
  selectedFile.value = file
  sourceDialogVisible.value = true
  
  try {
    const content = await getJarSourceFileContent(jarName.value, versionNo.value, file.file_path)
    selectedFileContent.value = content
  } catch (error) {
    console.error('Failed to load file content:', error)
    ElMessage.error('Failed to load file content')
    selectedFileContent.value = 'Error loading file content'
  }
}

const closeSourceDialog = () => {
  sourceDialogVisible.value = false
  selectedFile.value = null
  selectedFileContent.value = ''
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString) => {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Lifecycle
onMounted(() => {
  loadSourceFiles()
})
</script>

<style scoped>
.jar-sources-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e1e4e8;
}

.back-button {
  flex-shrink: 0;
}

.header-info {
  flex: 1;
}

.header-info h2 {
  font-size: 1.75rem;
  font-weight: 600;
  color: #24292f;
  margin: 0 0 0.5rem 0;
}

.page-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #656d76;
  font-size: 0.875rem;
  margin: 0;
}

.page-meta .el-icon {
  color: #6c757d;
}

.loading-container {
  padding: 2rem;
}

.sources-container {
  margin-top: 2rem;
}

.sources-table {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}

.empty-state {
  padding: 4rem 2rem;
  text-align: center;
}

.source-viewer {
  max-height: 70vh;
  overflow: hidden;
}

.source-header {
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e1e4e8;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.last-modified {
  color: #656d76;
  font-size: 0.875rem;
}

.source-content {
  max-height: 60vh;
  overflow: auto;
  background: #f8f9fa;
  border-radius: 6px;
  padding: 1rem;
}

.source-content pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  color: #24292f;
}

.source-content code {
  background: none;
  padding: 0;
}

/* Responsive Design */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-info h2 {
    font-size: 1.5rem;
  }
  
  .sources-table {
    overflow-x: auto;
  }
  
  .file-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>

<template>
  <div class="jar-unified-diff">
    <div class="header">
      <h2>{{ title }}</h2>
      <div v-if="summary" class="summary">
        <span class="stat added">+{{ summary.insertions }}</span>
        <span class="stat removed">-{{ summary.deletions }}</span>
        <span class="stat files">{{ summary.files_changed }} files</span>
      </div>
    </div>

    <div class="toolbar">
      <el-input v-model="keyword" placeholder="过滤文件路径" size="small" clearable style="max-width: 320px" />
      <el-checkbox v-model="showAllFiles" label="显示所有文件" size="small" />
    </div>

    <div v-if="loading" class="loading">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else>
        <div v-for="f in filteredFiles" :key="f.file_path" class="file-block">
          <div class="file-header">
            <h4>{{ f.file_path }}</h4>
            <div class="file-header-right">
              <div class="file-stats">
                <span v-if="f.change_type === 'unchanged'" class="stat unchanged">无变化</span>
                <template v-else>
                  <span class="stat added">+{{ f.additions }}</span>
                  <span class="stat removed">-{{ f.deletions }}</span>
                </template>
              </div>
              <div class="file-actions" v-if="itemType === 'jar' || itemType === 'class'">
                <el-button 
                  type="primary" 
                  link 
                  size="small"
                  @click="viewSource(fromVersion, f.class_full_name, f.change_type)"
                >
                  查看源码
                </el-button>
              </div>
            </div>
          </div>
          <Diff2HtmlBlock v-if="f.unified_diff" :unified-diff="f.unified_diff" :file-path="f.file_path" />
        </div>
    </div>
    
    <!-- 源码查看弹窗 -->
    <el-dialog
      v-model="sourceDialogVisible"
      :title="selectedFile ? `${selectedFile.class_full_name} - Version ${selectedFile.version}` : ''"
      width="80%"
      :close-on-click-modal="false"
    >
      <div class="source-content">
        <pre><code>{{ selectedFileContent }}</code></pre>
      </div>
      <template #footer>
        <el-button @click="sourceDialogVisible = false">Close</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import Diff2HtmlBlock from '@/components/Diff2HtmlBlock.vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const route = useRoute()
const loading = ref(true)
const files = ref([])
const summary = ref(null)
const keyword = ref('')
const showAllFiles = ref(false)
const sourceDialogVisible = ref(false)
const selectedFile = ref(null)
const selectedFileContent = ref('')

const itemType = computed(() => route.params.type)
const itemName = computed(() => decodeURIComponent(route.params.name))
const fromVersion = computed(() => route.params.fromVersion)
const toVersion = computed(() => route.params.toVersion)

const title = computed(() => `${itemName.value} 版本 ${fromVersion.value} → ${toVersion.value} 差异（单窗格）`)

const filteredFiles = computed(() => {
  return files.value.filter(f => {
    const matchKeyword = !keyword.value || f.file_path.toLowerCase().includes(keyword.value.toLowerCase())
    // 默认只显示修改的文件，勾选"显示所有文件"后才显示所有文件
    const matchChanged = showAllFiles.value || f.additions + f.deletions > 0
    return matchKeyword && matchChanged
  })
})

const load = async () => {
  loading.value = true
  try {
    const apiUrl = itemType.value === 'jar' 
      ? `/api/jars/${encodeURIComponent(itemName.value)}/diff`
      : `/api/classes/${encodeURIComponent(itemName.value)}/diff`
    
    const { data } = await axios.get(apiUrl, {
      params: { from_version: fromVersion.value, to_version: toVersion.value, format: 'unified', include: 'diff' }
    })
    summary.value = data.summary
    // JAR API返回files，Class API返回file_changes
    files.value = data.files || data.file_changes || []
  } finally {
    loading.value = false
  }
}

const viewSource = async (version, classFullName, changeType) => {
  if ((itemType.value === 'jar' || itemType.value === 'class') && itemName.value) {
    if (changeType === 'unchanged') {
      // 无差异：弹窗显示源码
      try {
        let apiUrl
        if (itemType.value === 'jar') {
          // JAR文件：通过JAR源码API获取
          const filePath = classFullName.replace(/\./g, '/') + '.java'
          apiUrl = `/api/jars/${encodeURIComponent(itemName.value)}/sources/${version}/content`
          const response = await axios.get(apiUrl, {
            params: { file_path: filePath }
          })
          selectedFileContent.value = response.data.content || ''
        } else {
          // Class文件：通过Class源码API获取
          apiUrl = `/api/classes/${encodeURIComponent(itemName.value)}/sources/${version}/content`
          const response = await axios.get(apiUrl, {
            params: { file_path: classFullName.replace(/\./g, '/') + '.java' }
          })
          selectedFileContent.value = response.data.content || ''
        }
        
        // 设置弹窗内容
        selectedFile.value = {
          class_full_name: classFullName,
          version: version
        }
        sourceDialogVisible.value = true
      } catch (error) {
        console.error('Failed to load source content:', error)
        ElMessage.error('Failed to load source content')
      }
    } else {
      // 有差异：跳转到双窗格源码展示页面
      if (itemType.value === 'jar') {
        const jarName = encodeURIComponent(itemName.value)
        const encodedClassName = encodeURIComponent(classFullName)
        window.open(`/diff/jar-file/${jarName}/${fromVersion.value}/${toVersion.value}?class_full_name=${encodedClassName}`, '_blank')
      } else {
        // Class文件：跳转到Class双窗格页面
        const className = encodeURIComponent(itemName.value)
        const encodedClassName = encodeURIComponent(classFullName)
        window.open(`/diff/class-file/${className}/${fromVersion.value}/${toVersion.value}?class_full_name=${encodedClassName}`, '_blank')
      }
    }
  }
}

onMounted(load)
</script>

<style scoped>
.jar-unified-diff { max-width: 1280px; margin: 0 auto; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.summary { display: flex; gap: 8px; }
.stat { font-weight: 600; font-size: 12px; padding: 2px 6px; border-radius: 3px; }
.stat.added { color: #1a7f37; background: #dafbe1; }
.stat.removed { color: #cf222e; background: #ffebe9; }
.stat.files { color: #656d76; background: #f3f4f6; }
.stat.unchanged { color: #656d76; background: #f3f4f6; }
.toolbar { display: flex; gap: 12px; margin: 12px 0; }
.file-block { margin-bottom: 24px; border: 1px solid #d0d7de; border-radius: 6px; overflow: hidden; }
.file-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #f6f8fa; border-bottom: 1px solid #d0d7de; }
.file-header-right { display: flex; align-items: center; gap: 1rem; }
.file-stats { display: flex; gap: 8px; }
.file-actions { display: flex; gap: 0.5rem; }
.file-header h4 { margin: 0; font-family: ui-monospace, SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace; }
.loading { padding: 24px; }

.source-content {
  max-height: 70vh;
  overflow: auto;
  background: #f8f9fa;
  border-radius: 6px;
  padding: 16px;
}

.source-content pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.4;
  color: #24292f;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.source-content code {
  background: transparent;
  padding: 0;
  border: none;
  font-family: inherit;
}
</style>

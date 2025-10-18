<template>
  <div class="java-source-details-page">
    <div class="page-header">
      <el-button @click="goBack" icon="ArrowLeft" size="small">Back</el-button>
      <h1>{{ classFullName }}</h1>
      <p class="page-description">Java source file version history and usage</p>
    </div>

    <div class="content" v-loading="loading">
      <!-- Version History Section -->
      <div class="section" v-if="versions.length > 0">
        <h2>Version History</h2>
        <div class="version-timeline">
          <div 
            v-for="(version, index) in versions" 
            :key="version.version"
            class="version-item"
          >
            <div class="version-marker">
              <div class="version-number">{{ version.version }}</div>
            </div>
            
            <div class="version-content">
              <div class="version-header">
                <div class="version-info">
                  <h3 class="version-title">Version {{ version.version }}</h3>
                  <div class="version-meta">
                    <el-tag size="small" type="info">{{ formatFileSize(version.file_size) }}</el-tag>
                    <el-tag 
                      v-if="version.file_hash" 
                      size="small" 
                      type="success" 
                      class="source-hash-tag"
                      :title="version.file_hash"
                    >
                      <el-icon><Key /></el-icon>
                      {{ version.file_hash.substring(0, 12) }}...
                    </el-tag>
                    <span class="version-count">{{ version.service_count }} services</span>
                  </div>
                </div>
                <div class="version-actions">
                  <el-button 
                    v-if="index > 0" 
                    type="primary" 
                    size="small"
                    @click="showDiff(versions[index].version, versions[index-1].version)"
                  >
                    <el-icon><Switch /></el-icon>
                    View Differences
                  </el-button>

                  <el-button size="small" @click="viewSource(version.version)">
                    <el-icon><View /></el-icon>
                    View Source
                  </el-button>
                </div>
              </div>
              
              <div class="version-details">
                <div class="time-range" v-if="version.created_at">
                  <el-icon><Clock /></el-icon>
                  <span>{{ formatDateTime(version.created_at) }}</span>
                </div>
                
                <!-- Services Section -->
                <div class="services-section">
                  <div class="services-header">
                    <el-icon><OfficeBuilding /></el-icon>
                    <span>Services using this version ({{ version.service_count }})</span>
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

                <!-- JAR Files Section -->
                <div class="files-section" v-if="version.jar_files.length > 0">
                  <div class="files-header">
                    <el-icon><FolderOpened /></el-icon>
                    <span>JAR Files ({{ version.jar_files.length }})</span>
                  </div>
                  <div class="files-list">
                    <div 
                      v-for="jar in version.jar_files" 
                      :key="`${jar.jar_name}-${jar.version_no}`"
                      class="file-item"
                    >
                      <el-link type="primary" @click="viewJarHistory(jar.jar_name)">
                        {{ jar.jar_name }} (v{{ jar.version_no }})
                      </el-link>
                      <el-tag 
                        v-if="jar.version_no !== jar.last_version_no" 
                        size="small" 
                        type="danger"
                        class="not-latest-tag"
                      >
                        Not Latest
                      </el-tag>
                      <span class="file-service">{{ jar.service_name }}</span>
                    </div>
                  </div>
                </div>

                <!-- Class Files Section -->
                <div class="files-section" v-if="version.class_files.length > 0">
                  <div class="files-header">
                    <el-icon><Document /></el-icon>
                    <span>Class Files ({{ version.class_files.length }})</span>
                  </div>
                  <div class="files-list">
                    <div 
                      v-for="classFile in version.class_files" 
                      :key="`${classFile.class_full_name}-${classFile.version_no}`"
                      class="file-item"
                    >
                      <el-link type="primary" @click="viewClassHistory(classFile.class_full_name)">
                        {{ classFile.class_full_name }} (v{{ classFile.version_no }})
                      </el-link>
                      <el-tag 
                        v-if="classFile.version_no !== classFile.last_version_no" 
                        size="small" 
                        type="danger"
                        class="not-latest-tag"
                      >
                        Not Latest
                      </el-tag>
                      <span class="file-service">{{ classFile.service_name }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Diff Section -->
      <div class="section" v-if="diffData">
        <div class="diff-header">
          <h2>Version Differences</h2>
          <div class="diff-summary">
            <span class="stat added">+{{ diffData.additions }}</span>
            <span class="stat removed">-{{ diffData.deletions }}</span>
            <span class="stat files">{{ diffData.files_changed }} files changed</span>
          </div>
        </div>
        
        <div class="diff-content">
          <div class="file-block">
            <div class="file-header">
              <h4>{{ diffData.class_full_name }}</h4>
              <div class="file-header-right">
                <div class="file-stats">
                  <span class="stat added">+{{ diffData.additions }}</span>
                  <span class="stat removed">-{{ diffData.deletions }}</span>
                </div>
                <div class="file-actions">
                  <el-button 
                    type="primary" 
                    link 
                    size="small"
                    @click="viewSource(diffData.from_version)"
                  >
                    View Old Version Source
                  </el-button>
                  <el-button 
                    type="primary" 
                    link 
                    size="small"
                    @click="viewSource(diffData.to_version)"
                  >
                    View New Version Source
                  </el-button>
                </div>
              </div>
            </div>
            <Diff2HtmlBlock 
              v-if="diffData.unified_diff" 
              :unified-diff="diffData.unified_diff" 
              :file-path="diffData.class_full_name" 
            />
          </div>
        </div>
      </div>

      <!-- No Data Message -->
      <div v-if="!loading && versions.length === 0" class="no-data">
        <el-empty description="No version data available" />
      </div>
    </div>
    
    <!-- Source View Dialog -->
    <el-dialog
      v-model="sourceDialogVisible"
      :title="selectedVersion ? `${classFullName} - Version ${selectedVersion}` : ''"
      width="80%"
      :close-on-click-modal="false"
    >
      <div class="source-content" v-loading="sourceLoading">
        <pre><code>{{ selectedSourceContent }}</code></pre>
      </div>
      <template #footer>
        <el-button @click="sourceDialogVisible = false">Close</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getJavaSourceVersions, getJavaSourceDiff } from '@/api/javaSources'
import Diff2HtmlBlock from '@/components/Diff2HtmlBlock.vue'
import axios from 'axios'

export default {
  name: 'JavaSourceDetailsPage',
  components: {
    Diff2HtmlBlock
  },
  setup() {
    const router = useRouter()
    const route = useRoute()
    const versions = ref([])
    const diffData = ref(null)
    const loading = ref(false)
    const sourceDialogVisible = ref(false)
    const selectedVersion = ref(null)
    const selectedSourceContent = ref('')
    const sourceLoading = ref(false)

    const classFullName = computed(() => {
      return route.params.classFullName ? decodeURIComponent(route.params.classFullName) : ''
    })

    const loadVersions = async () => {
      if (!classFullName.value) return
      
      try {
        loading.value = true
        const data = await getJavaSourceVersions(classFullName.value)
        versions.value = data
      } catch (error) {
        console.error('Failed to load versions:', error)
        ElMessage.error('Failed to load version history')
      } finally {
        loading.value = false
      }
    }

    const showDiff = async (fromVersion, toVersion) => {
      try {
        const data = await getJavaSourceDiff(classFullName.value, fromVersion, toVersion)
        diffData.value = data
        // Scroll to diff section
        setTimeout(() => {
          const diffSection = document.querySelector('.diff-header')
          if (diffSection) {
            diffSection.scrollIntoView({ behavior: 'smooth' })
          }
        }, 100)
      } catch (error) {
        console.error('Failed to load diff:', error)
        ElMessage.error('Failed to load differences')
      }
    }

    const viewSource = async (version) => {
      try {
        sourceLoading.value = true
        selectedVersion.value = version
        
        // Get source content for the specific version
        const response = await axios.get(
          `http://localhost:8000/api/java-sources/${encodeURIComponent(classFullName.value)}/versions`
        )
        
        const versionData = response.data.find(v => v.version === version)
        if (versionData) {
          // Get source content from the first JAR or Class file containing this version
          let sourceContent = ''
          
          if (versionData.jar_files.length > 0) {
            const jarFile = versionData.jar_files[0]
            const sourceResponse = await axios.get(
              `http://localhost:8000/api/jars/${encodeURIComponent(jarFile.jar_name)}/sources/${jarFile.version_no}/content`,
              { params: { class_full_name: classFullName.value } }
            )
            sourceContent = sourceResponse.data.content || ''
          } else if (versionData.class_files.length > 0) {
            const classFile = versionData.class_files[0]
            const sourceResponse = await axios.get(
              `http://localhost:8000/api/classes/${encodeURIComponent(classFile.class_full_name)}/sources/${classFile.version_no}/content`,
              { params: { class_full_name: classFullName.value } }
            )
            sourceContent = sourceResponse.data.content || ''
          }
          
          selectedSourceContent.value = sourceContent
          sourceDialogVisible.value = true
        }
      } catch (error) {
        console.error('Failed to load source:', error)
        ElMessage.error('Failed to load source content')
      } finally {
        sourceLoading.value = false
      }
    }

    const goBack = () => {
      router.go(-1)
    }

    const viewJarHistory = (jarName) => {
      router.push(`/history/jar/${encodeURIComponent(jarName)}`)
    }

    const viewClassHistory = (className) => {
      router.push(`/history/class/${encodeURIComponent(className)}`)
    }

    const formatDateTime = (dateTimeString) => {
      if (!dateTimeString) return '-'
      const date = new Date(dateTimeString)
      return date.toLocaleString('en-CA', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      }).replace(',', '')
    }

    const formatFileSize = (bytes) => {
      if (!bytes) return '-'
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(1024))
      return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
    }

    onMounted(() => {
      loadVersions()
    })

    return {
      versions,
      diffData,
      loading,
      sourceDialogVisible,
      selectedVersion,
      selectedSourceContent,
      sourceLoading,
      classFullName,
      goBack,
      viewJarHistory,
      viewClassHistory,
      showDiff,
      viewSource,
      formatDateTime,
      formatFileSize
    }
  }
}
</script>

<style scoped>
.java-source-details-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-header h1 {
  margin: 0;
  color: #303133;
  font-size: 28px;
  font-weight: 600;
}

.page-description {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.section {
  padding: 24px;
  border-bottom: 1px solid #ebeef5;
}

.section:last-child {
  border-bottom: none;
}

.section h2 {
  margin: 0 0 16px 0;
  color: #303133;
  font-size: 18px;
  font-weight: 600;
}

/* Version Timeline Styles */
.version-timeline {
  position: relative;
}

.version-item {
  display: flex;
  margin-bottom: 24px;
  position: relative;
}

.version-item:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 20px;
  top: 40px;
  bottom: -24px;
  width: 2px;
  background: #e4e7ed;
}

.version-marker {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #409eff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  flex-shrink: 0;
  z-index: 1;
}

.version-number {
  color: white;
  font-weight: bold;
  font-size: 14px;
}

.version-content {
  flex: 1;
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
}

.version-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.version-title {
  margin: 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.version-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.version-count {
  color: #606266;
  font-size: 12px;
}

.version-actions {
  display: flex;
  gap: 8px;
}

.version-details {
  margin-top: 12px;
}

.time-range {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #606266;
  font-size: 12px;
  margin-bottom: 12px;
}

.services-section, .files-section {
  margin-bottom: 12px;
}

.services-header, .files-header {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #303133;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
}

.services-list, .files-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.service-tag {
  cursor: pointer;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  background: white;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
  font-size: 12px;
}

.not-latest-tag {
  margin-left: 4px;
}

.file-service {
  color: #909399;
  font-size: 11px;
}

.source-hash-tag {
  max-width: 120px;
}

/* Diff Section Styles */
.diff-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.diff-summary {
  display: flex;
  gap: 12px;
}

.stat {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.stat.added {
  background: #f0f9ff;
  color: #1890ff;
}

.stat.removed {
  background: #fff2f0;
  color: #ff4d4f;
}

.stat.files {
  background: #f6ffed;
  color: #52c41a;
}

.diff-content {
  background: #f8f9fa;
  border-radius: 8px;
  overflow: hidden;
}

.file-block {
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
}

.file-header h4 {
  margin: 0;
  color: #303133;
  font-size: 14px;
  font-weight: 500;
}

.file-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-stats {
  display: flex;
  gap: 8px;
}

.file-actions {
  display: flex;
  gap: 8px;
}

/* Source Dialog Styles */
.source-content {
  max-height: 60vh;
  overflow: auto;
  background: #f8f9fa;
  border-radius: 4px;
  padding: 16px;
}

.source-content pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #303133;
}

.source-content code {
  background: none;
  padding: 0;
}

.text-muted {
  color: #909399;
}

.no-data {
  padding: 40px;
  text-align: center;
}
</style>
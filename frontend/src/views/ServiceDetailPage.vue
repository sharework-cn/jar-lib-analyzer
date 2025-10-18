<template>
  <div class="service-detail-page">
    <div class="page-header">
      <el-button 
        type="primary" 
        :icon="ArrowLeft" 
        @click="goBack"
        class="back-button"
      >
        Back to Services
      </el-button>
      <div class="header-info">
        <h2>{{ serviceName }}</h2>
        <p class="service-meta">
          <el-icon><Clock /></el-icon>
          Last updated: {{ formatDate(serviceData?.last_updated) }}
        </p>
      </div>
    </div>

    <!-- Loading State -->
    <div class="loading-container" v-if="loading">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- Service Content -->
    <div class="service-content" v-if="!loading && serviceData">
      <!-- JAR Files Section -->
      <div class="section" v-if="jarFiles.length > 0">
        <h3 class="section-title">
          <el-icon><Box /></el-icon>
          JAR Files ({{ jarFiles.length }})
        </h3>
        <div class="files-table">
          <el-table :data="jarFiles" stripe>
            <el-table-column prop="jar_name" label="JAR Name" min-width="200">
              <template #default="{ row }">
                <el-button 
                  type="primary" 
                  link 
                  @click="goToJarHistory(row.jar_name)"
                >
                  {{ row.jar_name }}
                </el-button>
              </template>
            </el-table-column>
            <el-table-column prop="version_no" label="Version" width="180" align="center">
              <template #default="{ row }">
                <div class="version-cell">
                  <span class="version-number">{{ row.version_no }}</span>
                  <el-tag 
                    v-if="!isLatestVersion(row, 'jar')" 
                    type="warning" 
                    size="small" 
                    class="version-tag clickable-tag"
                    @click="viewVersionDiff(row, 'jar')"
                  >
                    Not Latest
                  </el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="file_size" label="Size" width="120" align="right">
              <template #default="{ row }">
                {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column prop="last_modified" label="Last Modified" width="180">
              <template #default="{ row }">
                {{ formatDate(row.last_modified) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- Class Files Section -->
      <div class="section" v-if="classFiles.length > 0">
        <h3 class="section-title">
          <el-icon><Document /></el-icon>
          Class Files ({{ classFiles.length }})
        </h3>
        <div class="files-table">
          <el-table :data="classFiles" stripe>
            <el-table-column prop="class_full_name" label="Class Name" min-width="300">
              <template #default="{ row }">
                <el-button 
                  type="success" 
                  link 
                  @click="goToClassHistory(row.class_full_name)"
                >
                  {{ row.class_full_name }}
                </el-button>
              </template>
            </el-table-column>
            <el-table-column prop="version_no" label="Version" width="180" align="center">
              <template #default="{ row }">
                <div class="version-cell">
                  <span class="version-number">{{ row.version_no }}</span>
                  <el-tag 
                    v-if="!isLatestVersion(row, 'class')" 
                    type="warning" 
                    size="small" 
                    class="version-tag clickable-tag"
                    @click="viewVersionDiff(row, 'class')"
                  >
                    Not Latest
                  </el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="file_size" label="Size" width="120" align="right">
              <template #default="{ row }">
                {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column prop="last_modified" label="Last Modified" width="180">
              <template #default="{ row }">
                {{ formatDate(row.last_modified) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- Empty State -->
      <div class="empty-state" v-if="jarFiles.length === 0 && classFiles.length === 0">
        <el-empty description="No JAR or Class files found for this service" />
      </div>
    </div>

    <!-- Error State -->
    <div class="error-state" v-if="!loading && !serviceData">
      <el-empty description="Service not found" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Clock, Box, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getServiceDetail } from '@/api/services'

const route = useRoute()
const router = useRouter()

// Reactive data
const loading = ref(true)
const serviceData = ref(null)

// Computed properties
const serviceName = computed(() => {
  return serviceData.value?.service_name || 'Unknown Service'
})

const jarFiles = computed(() => {
  return serviceData.value?.jar_files || []
})

const classFiles = computed(() => {
  return serviceData.value?.class_files || []
})

// Methods
const loadServiceDetail = async () => {
  loading.value = true
  try {
    const serviceId = route.params.id
    const data = await getServiceDetail(serviceId)
    serviceData.value = data
  } catch (error) {
    console.error('Failed to load service detail:', error)
    ElMessage.error('Failed to load service details')
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/services')
}

const goToJarHistory = (jarName) => {
  router.push(`/history/jar/${encodeURIComponent(jarName)}`)
}

const goToClassHistory = (className) => {
  router.push(`/history/class/${encodeURIComponent(className)}`)
}

// Check if version is latest
const isLatestVersion = (item, type) => {
  // Use last_version_no field to determine if this is the latest version
  return item.version_no === item.last_version_no
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
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

const viewVersionDiff = (row, type) => {
  const currentVersion = row.version_no
  const latestVersion = row.last_version_no
  
  if (type === 'jar') {
    router.push(`/diff-unified/jar/${row.jar_name}/${currentVersion}/${latestVersion}`)
  } else if (type === 'class') {
    router.push(`/diff-unified/class/${row.class_full_name}/${currentVersion}/${latestVersion}`)
  }
}

// Lifecycle
onMounted(() => {
  loadServiceDetail()
})
</script>

<style scoped>
.service-detail-page {
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

.service-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #656d76;
  font-size: 0.875rem;
  margin: 0;
}

.service-meta .el-icon {
  color: #6c757d;
}

.loading-container {
  padding: 2rem;
}

.service-content {
  margin-top: 2rem;
}

.section {
  margin-bottom: 3rem;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  font-weight: 600;
  color: #24292f;
  margin-bottom: 1rem;
}

.section-title .el-icon {
  color: #409eff;
}

.files-table {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}

.empty-state,
.error-state {
  padding: 4rem 2rem;
  text-align: center;
}

.version-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.version-number {
  font-weight: 600;
  color: #24292f;
}

.version-tag {
  font-size: 0.75rem;
  animation: pulse 2s infinite;
}

.clickable-tag {
  cursor: pointer;
  transition: all 0.2s ease;
}

.clickable-tag:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
  100% {
    opacity: 1;
  }
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
  
  .files-table {
    overflow-x: auto;
  }
}
</style>

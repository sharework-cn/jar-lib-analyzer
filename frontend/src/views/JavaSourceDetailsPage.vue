<template>
  <div class="java-source-details-page">
    <div class="page-header">
      <el-button @click="goBack" icon="ArrowLeft" size="small">Back</el-button>
      <h1>{{ classFullName }}</h1>
      <p class="page-description">Java source file details and usage</p>
    </div>

    <div class="content" v-loading="loading">
      <div v-if="sourceDetails">
        <!-- JAR Files Section -->
        <div class="section" v-if="sourceDetails.jar_files.length > 0">
          <h2>JAR Files Containing This Source</h2>
          <el-table :data="sourceDetails.jar_files" stripe style="width: 100%">
            <el-table-column prop="jar_name" label="JAR Name" min-width="300">
              <template #default="{ row }">
                <el-link type="primary" @click="viewJarHistory(row.jar_name)">
                  {{ row.jar_name }}
                </el-link>
              </template>
            </el-table-column>
            
            <el-table-column prop="version_no" label="Version" width="100" align="center">
              <template #default="{ row }">
                <el-tag type="info">{{ row.version_no }}</el-tag>
              </template>
            </el-table-column>
            
            <el-table-column prop="last_version_no" label="Latest" width="100" align="center">
              <template #default="{ row }">
                <el-tag 
                  :type="row.version_no === row.last_version_no ? 'success' : 'danger'"
                  v-if="row.last_version_no"
                >
                  {{ row.last_version_no }}
                </el-tag>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            
            <el-table-column prop="source_version" label="Source Version" width="120" align="center">
              <template #default="{ row }">
                <el-tag type="warning">{{ row.source_version }}</el-tag>
              </template>
            </el-table-column>
            
            <el-table-column prop="last_modified" label="Last Modified" width="180">
              <template #default="{ row }">
                <span v-if="row.last_modified">
                  {{ formatDateTime(row.last_modified) }}
                </span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            
            <el-table-column prop="file_size" label="Size" width="100" align="right">
              <template #default="{ row }">
                {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            
            <el-table-column label="Actions" width="120" align="center">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  size="small"
                  @click="viewJarHistory(row.jar_name)"
                >
                  View History
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- Class Files Section -->
        <div class="section" v-if="sourceDetails.class_files.length > 0">
          <h2>Class Files Containing This Source</h2>
          <el-table :data="sourceDetails.class_files" stripe style="width: 100%">
            <el-table-column prop="class_full_name" label="Class Name" min-width="300">
              <template #default="{ row }">
                <el-link type="primary" @click="viewClassHistory(row.class_full_name)">
                  {{ row.class_full_name }}
                </el-link>
              </template>
            </el-table-column>
            
            <el-table-column prop="version_no" label="Version" width="100" align="center">
              <template #default="{ row }">
                <el-tag type="info">{{ row.version_no }}</el-tag>
              </template>
            </el-table-column>
            
            <el-table-column prop="last_version_no" label="Latest" width="100" align="center">
              <template #default="{ row }">
                <el-tag 
                  :type="row.version_no === row.last_version_no ? 'success' : 'danger'"
                  v-if="row.last_version_no"
                >
                  {{ row.last_version_no }}
                </el-tag>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            
            <el-table-column prop="source_version" label="Source Version" width="120" align="center">
              <template #default="{ row }">
                <el-tag type="warning">{{ row.source_version }}</el-tag>
              </template>
            </el-table-column>
            
            <el-table-column prop="last_modified" label="Last Modified" width="180">
              <template #default="{ row }">
                <span v-if="row.last_modified">
                  {{ formatDateTime(row.last_modified) }}
                </span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            
            <el-table-column prop="file_size" label="Size" width="100" align="right">
              <template #default="{ row }">
                {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            
            <el-table-column label="Actions" width="120" align="center">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  size="small"
                  @click="viewClassHistory(row.class_full_name)"
                >
                  View History
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- No Data Message -->
        <div v-if="sourceDetails.jar_files.length === 0 && sourceDetails.class_files.length === 0" class="no-data">
          <el-empty description="No JAR or Class files found containing this source" />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getJavaSourceDetails } from '@/api/javaSources'

export default {
  name: 'JavaSourceDetailsPage',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const sourceDetails = ref(null)
    const loading = ref(false)

    const classFullName = computed(() => {
      return route.params.classFullName ? decodeURIComponent(route.params.classFullName) : ''
    })

    const loadSourceDetails = async () => {
      if (!classFullName.value) return
      
      try {
        loading.value = true
        const data = await getJavaSourceDetails(classFullName.value)
        sourceDetails.value = data
      } catch (error) {
        console.error('Failed to load source details:', error)
        ElMessage.error('Failed to load source details')
      } finally {
        loading.value = false
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
      loadSourceDetails()
    })

    return {
      sourceDetails,
      loading,
      classFullName,
      goBack,
      viewJarHistory,
      viewClassHistory,
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

.text-muted {
  color: #909399;
}

.no-data {
  padding: 40px;
  text-align: center;
}
</style>

<template>
  <div class="jars-page">
    <div class="page-header">
      <h1>JAR Files</h1>
      <p class="page-description">Browse all JAR files in the system</p>
    </div>

    <div class="content">
      <el-table
        v-loading="loading"
        :data="jars"
        stripe
        style="width: 100%"
        @row-click="handleRowClick"
        class="jars-table"
      >
        <el-table-column prop="jar_name" label="JAR Name" min-width="300">
          <template #default="{ row }">
            <div class="jar-name-cell">
              <el-link type="primary" @click.stop="viewJarHistory(row.jar_name)">
                {{ row.jar_name }}
              </el-link>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="service_count" label="Services" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="success">{{ row.service_count }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="version_count" label="Versions" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info">{{ row.version_count }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="earliest_modified" label="Earliest Modified" width="180">
          <template #default="{ row }">
            <span v-if="row.earliest_modified">
              {{ formatDateTime(row.earliest_modified) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="latest_modified" label="Latest Modified" width="180">
          <template #default="{ row }">
            <span v-if="row.latest_modified">
              {{ formatDateTime(row.latest_modified) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        
        <el-table-column label="Actions" width="120" align="center">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click.stop="viewJarHistory(row.jar_name)"
            >
              View History
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Load More Button -->
      <div class="load-more-container" v-if="hasMore">
        <el-button
          type="primary"
          :loading="loadingMore"
          @click="loadMore"
          size="large"
        >
          Load More
        </el-button>
      </div>

      <!-- No More Data Message -->
      <div class="no-more-data" v-if="!hasMore && jars.length > 0">
        <el-text type="info">No more JAR files to load</el-text>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getJars } from '@/api/jars'

export default {
  name: 'JarsPage',
  setup() {
    const router = useRouter()
    const jars = ref([])
    const loading = ref(false)
    const loadingMore = ref(false)
    const hasMore = ref(true)
    const lastJarName = ref(null)
    const pageSize = ref(100)

    const loadJars = async (isLoadMore = false) => {
      try {
        if (isLoadMore) {
          loadingMore.value = true
        } else {
          loading.value = true
        }
        
        const response = await getJars(pageSize.value, lastJarName.value)
        
        if (isLoadMore) {
          jars.value.push(...response.data)
        } else {
          jars.value = response.data
        }
        
        hasMore.value = response.has_more
        lastJarName.value = response.last_jar_name
      } catch (error) {
        console.error('Failed to load JARs:', error)
        ElMessage.error('Failed to load JARs')
      } finally {
        loading.value = false
        loadingMore.value = false
      }
    }

    const handleRowClick = (row) => {
      viewJarHistory(row.jar_name)
    }

    const viewJarHistory = (jarName) => {
      router.push(`/history/jar/${encodeURIComponent(jarName)}`)
    }

    const loadMore = () => {
      loadJars(true)
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

    onMounted(() => {
      loadJars()
    })

    return {
      jars,
      loading,
      loadingMore,
      hasMore,
      handleRowClick,
      viewJarHistory,
      loadMore,
      formatDateTime
    }
  }
}
</script>

<style scoped>
.jars-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0 0 8px 0;
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

.jars-table {
  cursor: pointer;
}

.jar-name-cell {
  font-weight: 500;
}

.text-muted {
  color: #909399;
}

.load-more-container {
  padding: 20px;
  text-align: center;
  border-top: 1px solid #ebeef5;
}

.no-more-data {
  padding: 20px;
  text-align: center;
  border-top: 1px solid #ebeef5;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>

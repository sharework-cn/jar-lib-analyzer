<template>
  <div class="java-sources-page">
    <div class="page-header">
      <h1>Java Sources</h1>
      <p class="page-description">Browse all Java source files in the system</p>
    </div>

    <div class="content">
      <el-table
        v-loading="loading"
        :data="javaSources"
        stripe
        style="width: 100%"
        @row-click="handleRowClick"
        class="sources-table"
      >
        <el-table-column prop="class_full_name" label="Class Name" min-width="400">
          <template #default="{ row }">
            <div class="class-name-cell">
              <el-link type="primary" @click.stop="viewSourceDetails(row.class_full_name)">
                {{ row.class_full_name }}
              </el-link>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="version_count" label="Versions" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info">{{ row.version_count }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="source_types" label="Source Types" width="150">
          <template #default="{ row }">
            <div class="source-types">
              <el-tag
                v-for="type in row.source_types"
                :key="type"
                :type="type === 'JAR' ? 'success' : 'warning'"
                size="small"
                class="source-type-tag"
              >
                {{ type }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="jar_count" label="JAR Files" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.jar_count > 0" type="success">{{ row.jar_count }}</el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="class_count" label="Class Files" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.class_count > 0" type="warning">{{ row.class_count }}</el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        
        <el-table-column label="Actions" width="120" align="center">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click.stop="viewSourceDetails(row.class_full_name)"
            >
              View Details
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
      <div class="no-more-data" v-if="!hasMore && javaSources.length > 0">
        <el-text type="info">No more Java sources to load</el-text>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getJavaSources } from '@/api/javaSources'

export default {
  name: 'JavaSourcesPage',
  setup() {
    const router = useRouter()
    const javaSources = ref([])
    const loading = ref(false)
    const loadingMore = ref(false)
    const hasMore = ref(true)
    const lastClassName = ref(null)
    const pageSize = ref(100)

    const loadJavaSources = async (isLoadMore = false) => {
      try {
        if (isLoadMore) {
          loadingMore.value = true
        } else {
          loading.value = true
        }
        
        const response = await getJavaSources(pageSize.value, lastClassName.value)
        
        if (isLoadMore) {
          javaSources.value.push(...response.data)
        } else {
          javaSources.value = response.data
        }
        
        hasMore.value = response.has_more
        lastClassName.value = response.last_class_name
      } catch (error) {
        console.error('Failed to load Java Sources:', error)
        ElMessage.error('Failed to load Java Sources')
      } finally {
        loading.value = false
        loadingMore.value = false
      }
    }

    const handleRowClick = (row) => {
      viewSourceDetails(row.class_full_name)
    }

    const viewSourceDetails = (classFullName) => {
      router.push(`/java-source-details/${encodeURIComponent(classFullName)}`)
    }

    const loadMore = () => {
      loadJavaSources(true)
    }

    onMounted(() => {
      loadJavaSources()
    })

    return {
      javaSources,
      loading,
      loadingMore,
      hasMore,
      handleRowClick,
      viewSourceDetails,
      loadMore
    }
  }
}
</script>

<style scoped>
.java-sources-page {
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

.sources-table {
  cursor: pointer;
}

.class-name-cell {
  font-weight: 500;
}

.source-types {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.source-type-tag {
  margin: 0;
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

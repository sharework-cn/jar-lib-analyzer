<template>
  <div class="critical-changes-page">
    <div class="page-header">
      <el-button 
        type="primary" 
        :icon="ArrowLeft" 
        @click="goBack"
        class="back-button"
      >
        Back
      </el-button>
      <div class="header-info">
        <h2>{{ pageTitle }}</h2>
        <p class="page-subtitle">Critical Compatibility Issues Analysis</p>
      </div>
    </div>

    <!-- Loading State -->
    <div class="loading-container" v-if="loading">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- Error State -->
    <div class="error-container" v-if="error">
      <el-alert
        :title="error"
        type="error"
        show-icon
        :closable="false"
      />
    </div>

    <!-- Critical Changes Content -->
    <div class="critical-changes-content" v-if="!loading && !error && criticalChanges.length > 0">
      <div class="summary-card">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><Warning /></el-icon>
              <span>Summary</span>
            </div>
          </template>
          <div class="summary-stats">
            <div class="stat-item">
              <div class="stat-number">{{ criticalChanges.length }}</div>
              <div class="stat-label">Total Issues</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">{{ highSeverityCount }}</div>
              <div class="stat-label">High Severity</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">{{ totalItems }}</div>
              <div class="stat-label">Total Items</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">{{ itemsWithDifferences }}</div>
              <div class="stat-label">Items with Differences</div>
            </div>
          </div>
        </el-card>
      </div>

      <div class="changes-list">
        <div 
          v-for="(change, index) in criticalChanges" 
          :key="index"
          class="change-item"
        >
          <el-card class="change-card" :class="change.severity">
            <template #header>
              <div class="change-header">
                <div class="change-type">
                  <el-icon v-if="change.type === 'jar_differences'"><Box /></el-icon>
                  <el-icon v-else-if="change.type === 'class_differences'"><Document /></el-icon>
                  <el-icon v-else><Warning /></el-icon>
                  <span class="type-label">{{ getTypeLabel(change.type) }}</span>
                </div>
                <div class="change-severity">
                  <el-tag 
                    :type="change.severity === 'high' ? 'danger' : 'warning'"
                    size="small"
                  >
                    {{ change.severity === 'high' ? 'High Risk' : 'Medium Risk' }}
                  </el-tag>
                </div>
              </div>
            </template>
            
            <div class="change-content">
              <div class="change-info">
                <div class="change-name">
                  <strong>{{ getChangeName(change) }}</strong>
                </div>
                <div class="change-versions">
                  <el-tag size="small" type="info">
                    Version {{ change.current_version }} → {{ change.latest_version }}
                  </el-tag>
                </div>
                <div class="change-status">
                  <el-tag 
                    v-if="change.has_critical_changes" 
                    type="danger" 
                    size="small"
                  >
                    <el-icon><Warning /></el-icon>
                    Critical Changes Detected
                  </el-tag>
                  <el-tag 
                    v-else 
                    type="success" 
                    size="small"
                  >
                    <el-icon><Check /></el-icon>
                    No Critical Changes
                  </el-tag>
                </div>
              </div>
              
              <div class="change-actions" v-if="change.has_critical_changes">
                <el-button 
                  type="primary" 
                  size="small"
                  @click="viewDetails(change)"
                >
                  View Details
                </el-button>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <!-- No Issues State -->
    <div class="no-issues-container" v-if="!loading && !error && criticalChanges.length === 0">
      <el-empty description="No critical compatibility issues found">
        <template #image>
          <el-icon size="64" color="#67c23a"><Check /></el-icon>
        </template>
        <el-button type="primary" @click="goBack">Go Back</el-button>
      </el-empty>
    </div>

    <!-- Details Dialog -->
    <el-dialog
      v-model="detailsDialogVisible"
      :title="selectedChange ? getChangeName(selectedChange) : ''"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="selectedChange" class="change-details">
        <div class="details-header">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Type">
              {{ getTypeLabel(selectedChange.type) }}
            </el-descriptions-item>
            <el-descriptions-item label="Versions">
              {{ selectedChange.current_version }} → {{ selectedChange.latest_version }}
            </el-descriptions-item>
            <el-descriptions-item label="Severity">
              <el-tag :type="selectedChange.severity === 'high' ? 'danger' : 'warning'">
                {{ selectedChange.severity === 'high' ? 'High Risk' : 'Medium Risk' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Status">
              <el-tag :type="selectedChange.has_critical_changes ? 'danger' : 'success'">
                {{ selectedChange.has_critical_changes ? 'Critical Changes Detected' : 'No Critical Changes' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>
        
        <div class="details-content" v-if="selectedChange.has_critical_changes">
          <h4>Critical Changes Detected:</h4>
          <div v-if="selectedChange.critical_changes && selectedChange.critical_changes.length > 0">
            <div v-for="(change, index) in selectedChange.critical_changes" :key="index" class="critical-change-item">
              <el-card shadow="hover" class="change-card">
                <div class="change-header">
                  <el-tag :type="change.severity === 'high' ? 'danger' : 'warning'" size="small">
                    {{ getChangeTypeLabel(change.type) }}
                  </el-tag>
                  <span class="change-title">{{ getChangeTitle(change) }}</span>
                </div>
                <div class="change-description">
                  {{ change.description }}
                </div>
                <div v-if="change.location" class="change-location">
                  <strong>Location:</strong> {{ change.location }}
                </div>
                <div v-if="change.details" class="change-details">
                  <strong>Details:</strong>
                  <pre class="diff-code">{{ change.details }}</pre>
                </div>
              </el-card>
            </div>
          </div>
          <div v-else>
            <p>This item has critical compatibility issues that may affect incremental deployment.</p>
            <p>Please review the detailed differences in the export or version history pages.</p>
          </div>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="detailsDialogVisible = false">Close</el-button>
        <el-button 
          type="primary" 
          @click="viewInHistory"
          v-if="selectedChange"
        >
          View in History
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  ArrowLeft, 
  Warning, 
  Check, 
  Box, 
  Document 
} from '@element-plus/icons-vue'
import { getCriticalDifferences } from '@/api/criticalChanges'

const route = useRoute()
const router = useRouter()

// Reactive data
const loading = ref(false)
const error = ref('')
const criticalChanges = ref([])
const totalItems = ref(0)
const itemsWithDifferences = ref(0)
const detailsDialogVisible = ref(false)
const selectedChange = ref(null)

// Computed properties
const pageTitle = computed(() => {
  const type = route.query.type
  const name = route.query.name
  if (type === 'service') {
    return `Service: ${name}`
  } else if (type === 'jar') {
    return `JAR: ${name}`
  }
  return 'Critical Changes Analysis'
})

const highSeverityCount = computed(() => {
  return criticalChanges.value.filter(change => change.severity === 'high').length
})

// Methods
const goBack = () => {
  router.go(-1)
}

const getTypeLabel = (type) => {
  switch (type) {
    case 'jar_differences':
      return 'JAR Differences'
    case 'class_differences':
      return 'Class Differences'
    default:
      return 'Unknown'
  }
}

const getChangeName = (change) => {
  if (change.jar_name) {
    return change.jar_name
  } else if (change.class_name) {
    return change.class_name
  }
  return 'Unknown'
}

const getChangeTypeLabel = (type) => {
  switch (type) {
    case 'removed_class':
      return 'Class Removed'
    case 'removed_method':
      return 'Method Removed'
    case 'modified_method_signature':
      return 'Method Modified'
    default:
      return 'Unknown Change'
  }
}

const getChangeTitle = (change) => {
  if (change.type === 'removed_class') {
    const className = change.description.split("'")[1].split('.').pop()
    return `Class Removed: ${className}`
  } else if (change.type === 'removed_method') {
    const methodName = change.description.split("'")[1].split('(')[0]
    return `Method Removed: ${methodName}`
  } else if (change.type === 'modified_method_signature') {
    const methodName = change.description.split("'")[1]
    return `Method Modified: ${methodName}`
  }
  return change.type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const viewDetails = (change) => {
  selectedChange.value = change
  detailsDialogVisible.value = true
}

const viewInHistory = () => {
  if (selectedChange.value) {
    const type = route.query.type
    if (type === 'service') {
      // Navigate to service detail page
      router.push(`/services/${route.query.id}`)
    } else if (type === 'jar') {
      // Navigate to jar version history
      router.push(`/history/jar/${encodeURIComponent(route.query.name)}`)
    }
  }
  detailsDialogVisible.value = false
}

const loadCriticalChanges = async () => {
  loading.value = true
  error.value = ''
  
  try {
    const type = route.query.type
    const id = route.query.id
    const name = route.query.name
    
    let response
    if (type === 'service') {
      response = await getCriticalDifferences('service', id)
    } else if (type === 'jar') {
      response = await getCriticalDifferences('jar', name)
    } else {
      throw new Error('Invalid type parameter')
    }
    
    criticalChanges.value = response.critical_changes || []
    totalItems.value = response.total_items || 0
    itemsWithDifferences.value = response.items_with_differences || 0
    
  } catch (err) {
    console.error('Failed to load critical changes:', err)
    error.value = err.message || 'Failed to load critical changes'
    ElMessage.error('Failed to load critical changes')
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadCriticalChanges()
})
</script>

<style scoped>
.critical-changes-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 30px;
}

.header-info h2 {
  margin: 0;
  color: #303133;
}

.page-subtitle {
  margin: 5px 0 0 0;
  color: #909399;
  font-size: 14px;
}

.loading-container,
.error-container,
.no-issues-container {
  margin-top: 50px;
}

.summary-card {
  margin-bottom: 30px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.changes-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.change-card {
  transition: all 0.3s ease;
}

.change-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.change-card.high {
  border-left: 4px solid #f56c6c;
}

.change-card.medium {
  border-left: 4px solid #e6a23c;
}

.change-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.change-type {
  display: flex;
  align-items: center;
  gap: 8px;
}

.type-label {
  font-weight: 600;
}

.change-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.change-info {
  flex: 1;
}

.change-name {
  font-size: 16px;
  margin-bottom: 8px;
}

.change-versions,
.change-status {
  margin-bottom: 5px;
}

.change-actions {
  flex-shrink: 0;
}

.details-header {
  margin-bottom: 20px;
}

.details-content h4 {
  color: #f56c6c;
  margin-bottom: 10px;
}

.details-content p {
  margin-bottom: 10px;
  line-height: 1.6;
}

.critical-change-item {
  margin-bottom: 15px;
}

.change-card {
  margin-bottom: 10px;
}

.change-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.change-title {
  font-weight: bold;
  font-size: 16px;
}

.change-description {
  margin-bottom: 8px;
  color: #666;
}

.change-location {
  margin-bottom: 8px;
  font-size: 14px;
  color: #888;
}

.change-details {
  margin-top: 10px;
}

.change-details pre {
  margin-top: 5px;
}

.diff-code {
  background-color: #f0f0f0;
  padding: 10px;
  border-radius: 4px;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 14px;
}
</style>

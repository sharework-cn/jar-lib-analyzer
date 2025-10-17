<template>
  <div class="services-page">
    <div class="page-header">
      <h2>Services</h2>
      <p class="page-subtitle">View all services and their dependencies</p>
    </div>

    <!-- Loading State -->
    <div class="loading-container" v-if="loading">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- Services List -->
    <div class="services-container" v-if="!loading && services.length > 0">
      <div class="services-grid">
        <el-card 
          v-for="service in services" 
          :key="service.id"
          class="service-card"
          shadow="hover"
          @click="goToServiceDetail(service.id)"
        >
          <div class="card-content">
            <div class="card-header">
              <h3 class="service-name">{{ service.service_name }}</h3>
              <el-tag type="primary" size="small">SERVICE</el-tag>
            </div>
            <div class="card-stats">
              <div class="stat-item">
                <el-icon><Box /></el-icon>
                <span>{{ service.jar_count }} JAR files</span>
              </div>
              <div class="stat-item">
                <el-icon><Document /></el-icon>
                <span>{{ service.class_count }} Class files</span>
              </div>
            </div>
            <div class="card-meta">
              <div class="meta-item">
                <el-icon><Clock /></el-icon>
                <span>Last updated: {{ formatDate(service.last_updated) }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- Empty State -->
    <div class="empty-state" v-if="!loading && services.length === 0">
      <el-empty description="No services found" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Clock, Box, Document } from '@element-plus/icons-vue'
import { getServices } from '@/api/services'

const router = useRouter()

// Reactive data
const loading = ref(true)
const services = ref([])

// Methods
const loadServices = async () => {
  loading.value = true
  try {
    const data = await getServices()
    services.value = data
  } catch (error) {
    console.error('Failed to load services:', error)
    ElMessage.error('Failed to load services')
  } finally {
    loading.value = false
  }
}

const goToServiceDetail = (serviceId) => {
  router.push(`/services/${serviceId}`)
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
  loadServices()
})
</script>

<style scoped>
.services-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.page-header {
  text-align: center;
  margin-bottom: 2rem;
}

.page-header h2 {
  font-size: 2rem;
  font-weight: 600;
  color: #24292f;
  margin-bottom: 0.5rem;
}

.page-subtitle {
  color: #656d76;
  font-size: 1rem;
}

.loading-container {
  padding: 2rem;
}

.services-container {
  margin-top: 2rem;
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.service-card {
  cursor: pointer;
  transition: all 0.3s ease;
}

.service-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0,0,0,0.15);
}

.card-content {
  padding: 1rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.service-name {
  font-size: 1.25rem;
  font-weight: 600;
  color: #24292f;
  margin: 0;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #656d76;
  font-size: 0.875rem;
}

.stat-item .el-icon {
  color: #409eff;
}

.card-meta {
  border-top: 1px solid #e1e4e8;
  padding-top: 1rem;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #656d76;
  font-size: 0.875rem;
}

.meta-item .el-icon {
  color: #6c757d;
}

.empty-state {
  padding: 4rem 2rem;
  text-align: center;
}

/* Responsive Design */
@media (max-width: 768px) {
  .services-grid {
    grid-template-columns: 1fr;
  }
  
  .page-header h2 {
    font-size: 1.5rem;
  }
  
  .card-stats {
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style>

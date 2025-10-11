<template>
  <div class="search-page">
    <!-- 搜索区域 -->
    <div class="search-container">
      <div class="search-content">
        <h2 class="search-title">搜索JAR文件或Class文件</h2>
        <p class="search-subtitle">输入JAR名称或类名进行模糊搜索</p>
        
        <div class="search-input-group">
          <el-input
            v-model="searchQuery"
            placeholder="输入JAR名称或类名进行搜索..."
            size="large"
            clearable
            @keyup.enter="handleSearch"
            @input="handleInputChange"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button 
            type="primary" 
            size="large" 
            @click="handleSearch"
            :loading="loading"
          >
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
        </div>
        
        <div class="search-options">
          <el-radio-group v-model="searchType" size="default">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="jar">JAR文件</el-radio-button>
            <el-radio-button value="class">Class文件</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </div>

    <!-- 搜索结果 -->
    <div class="results-container" v-if="showResults">
      <div class="results-header">
        <h3>搜索结果</h3>
        <p class="results-count">共找到 {{ totalResults }} 个结果</p>
      </div>
      
      <!-- JAR文件结果 -->
      <div class="results-section" v-if="jarResults.length > 0">
        <h4 class="section-title">
          <el-icon><Box /></el-icon>
          JAR文件 ({{ jarResults.length }}个)
        </h4>
        <div class="results-grid">
          <el-card 
            v-for="jar in jarResults" 
            :key="jar.name"
            class="result-card"
            shadow="hover"
            @click="goToHistory('jar', jar.name)"
          >
            <div class="card-content">
              <div class="card-header">
                <h5 class="item-name">{{ jar.name }}</h5>
                <el-tag type="primary" size="small">JAR</el-tag>
              </div>
              <div class="card-stats">
                <div class="stat-item">
                  <el-icon><Document /></el-icon>
                  <span>{{ jar.file_count }}个文件</span>
                </div>
                <div class="stat-item">
                  <el-icon><Collection /></el-icon>
                  <span>{{ jar.version_count }}个版本</span>
                </div>
                <div class="stat-item">
                  <el-icon><OfficeBuilding /></el-icon>
                  <span>{{ jar.service_count }}个服务</span>
                </div>
              </div>
              <div class="card-services">
                <el-tag 
                  v-for="service in jar.services.slice(0, 3)" 
                  :key="service"
                  size="small"
                  class="service-tag"
                >
                  {{ service }}
                </el-tag>
                <span v-if="jar.services.length > 3" class="more-services">
                  +{{ jar.services.length - 3 }}个
                </span>
              </div>
            </div>
          </el-card>
        </div>
      </div>
      
      <!-- Class文件结果 -->
      <div class="results-section" v-if="classResults.length > 0">
        <h4 class="section-title">
          <el-icon><Document /></el-icon>
          Class文件 ({{ classResults.length }}个)
        </h4>
        <div class="results-grid">
          <el-card 
            v-for="cls in classResults" 
            :key="cls.name"
            class="result-card"
            shadow="hover"
            @click="goToHistory('class', cls.name)"
          >
            <div class="card-content">
              <div class="card-header">
                <h5 class="item-name">{{ cls.name }}</h5>
                <el-tag type="success" size="small">CLASS</el-tag>
              </div>
              <div class="card-stats">
                <div class="stat-item">
                  <el-icon><Document /></el-icon>
                  <span>{{ cls.file_count }}个文件</span>
                </div>
                <div class="stat-item">
                  <el-icon><Collection /></el-icon>
                  <span>{{ cls.version_count }}个版本</span>
                </div>
                <div class="stat-item">
                  <el-icon><OfficeBuilding /></el-icon>
                  <span>{{ cls.service_count }}个服务</span>
                </div>
              </div>
              <div class="card-services">
                <el-tag 
                  v-for="service in cls.services.slice(0, 3)" 
                  :key="service"
                  size="small"
                  class="service-tag"
                >
                  {{ service }}
                </el-tag>
                <span v-if="cls.services.length > 3" class="more-services">
                  +{{ cls.services.length - 3 }}个
                </span>
              </div>
            </div>
          </el-card>
        </div>
      </div>
      
      <!-- 无结果 -->
      <div class="no-results" v-if="!loading && totalResults === 0">
        <el-empty description="未找到匹配的结果">
          <el-button type="primary" @click="clearSearch">重新搜索</el-button>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Box, Document, Collection, OfficeBuilding } from '@element-plus/icons-vue'
import { searchItems } from '@/api/search'

const router = useRouter()

// 响应式数据
const searchQuery = ref('')
const searchType = ref('all')
const loading = ref(false)
const searchResults = ref({ jars: [], classes: [] })

// 计算属性
const showResults = computed(() => {
  return searchResults.value.jars.length > 0 || searchResults.value.classes.length > 0
})

const jarResults = computed(() => searchResults.value.jars)
const classResults = computed(() => searchResults.value.classes)
const totalResults = computed(() => jarResults.value.length + classResults.value.length)

// 方法
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    return
  }
  
  loading.value = true
  try {
    const results = await searchItems(searchQuery.value, searchType.value)
    searchResults.value = results
  } catch (error) {
    console.error('搜索失败:', error)
    ElMessage.error('搜索失败，请重试')
  } finally {
    loading.value = false
  }
}

const handleInputChange = () => {
  // 可以添加防抖搜索
}

const goToHistory = (type, name) => {
  router.push(`/history/${type}/${encodeURIComponent(name)}`)
}

const clearSearch = () => {
  searchQuery.value = ''
  searchResults.value = { jars: [], classes: [] }
}

// 监听搜索类型变化
watch(searchType, () => {
  if (searchQuery.value.trim()) {
    handleSearch()
  }
})
</script>

<style scoped>
.search-page {
  min-height: 100vh;
}

.search-container {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 3rem 0;
  margin: -2rem -2rem 2rem -2rem;
}

.search-content {
  max-width: 800px;
  margin: 0 auto;
  text-align: center;
  padding: 0 2rem;
}

.search-title {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.search-subtitle {
  font-size: 1.1rem;
  opacity: 0.9;
  margin-bottom: 2rem;
}

.search-input-group {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.search-input-group .el-input {
  flex: 1;
}

.search-options {
  display: flex;
  justify-content: center;
}

.results-container {
  max-width: 1200px;
  margin: 0 auto;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.results-header h3 {
  margin: 0;
  font-size: 1.5rem;
}

.results-count {
  color: #6c757d;
  margin: 0;
}

.results-section {
  margin-bottom: 3rem;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  font-size: 1.2rem;
  color: #495057;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 1rem;
}

.result-card {
  cursor: pointer;
  transition: all 0.3s ease;
}

.result-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.card-content {
  padding: 1rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.item-name {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #212529;
  word-break: break-all;
}

.card-stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: #6c757d;
}

.card-services {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.service-tag {
  margin: 0;
}

.more-services {
  font-size: 0.875rem;
  color: #6c757d;
}

.no-results {
  text-align: center;
  padding: 3rem 0;
}
</style>

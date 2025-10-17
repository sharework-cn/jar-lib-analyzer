<template>
  <div class="search-page">
    <!-- Search Area -->
    <div class="search-container">
      <div class="search-content">
        <h2 class="search-title">Search JAR Files or Class Files</h2>
        <p class="search-subtitle">Enter JAR name or class name for fuzzy search</p>
        
        <div class="search-input-group">
          <el-input
            v-model="searchQuery"
            placeholder="Enter JAR name or class name to search..."
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
            Search
          </el-button>
        </div>
        
        <div class="search-options">
          <el-radio-group v-model="searchType" size="default">
            <el-radio-button value="all">All</el-radio-button>
            <el-radio-button value="jar">JAR Files</el-radio-button>
            <el-radio-button value="class">Class Files</el-radio-button>
            <el-radio-button value="jar-source">JAR Source</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </div>

    <!-- Search Results -->
    <div class="results-container" v-if="showResults">
      <div class="results-header">
        <h3>Search Results</h3>
        <p class="results-count">Found {{ totalResults }} results</p>
      </div>
      
      <!-- JAR Files Results -->
      <div class="results-section" v-if="jarResults.length > 0">
        <h4 class="section-title">
          <el-icon><Box /></el-icon>
          JAR Files ({{ jarResults.length }})
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
                  <span>{{ jar.file_count }} files</span>
                </div>
                <div class="stat-item">
                  <el-icon><Collection /></el-icon>
                  <span>{{ jar.version_count }} versions</span>
                </div>
                <div class="stat-item">
                  <el-icon><OfficeBuilding /></el-icon>
                  <span>{{ jar.service_count }} services</span>
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
                  +{{ jar.services.length - 3 }} more
                </span>
              </div>
            </div>
          </el-card>
        </div>
      </div>
      
      <!-- Class Files Results -->
      <div class="results-section" v-if="classResults.length > 0">
        <h4 class="section-title">
          <el-icon><Document /></el-icon>
          Class Files ({{ classResults.length }})
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
                  <span>{{ cls.file_count }} files</span>
                </div>
                <div class="stat-item">
                  <el-icon><Collection /></el-icon>
                  <span>{{ cls.version_count }} versions</span>
                </div>
                <div class="stat-item">
                  <el-icon><OfficeBuilding /></el-icon>
                  <span>{{ cls.service_count }} services</span>
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
                  +{{ cls.services.length - 3 }} more
                </span>
              </div>
            </div>
          </el-card>
        </div>
      </div>
      
      <!-- JAR Source Results -->
      <div class="results-section" v-if="jarSourceResults.length > 0">
        <h4 class="section-title">
          <el-icon><Files /></el-icon>
          JAR Source Files ({{ jarSourceResults.length }})
        </h4>
        <div class="results-grid">
          <el-card 
            v-for="source in jarSourceResults" 
            :key="source.name"
            class="result-card"
            shadow="hover"
            @click="goToJarSource(source)"
          >
            <div class="card-content">
              <div class="card-header">
                <h5 class="item-name">{{ source.name }}</h5>
                <el-tag type="warning" size="small">JAR SOURCE</el-tag>
              </div>
              <div class="card-info">
                <div class="info-item">
                  <el-icon><Box /></el-icon>
                  <span>JAR: {{ source.jar_name }}</span>
                </div>
                <div class="info-item">
                  <el-icon><Document /></el-icon>
                  <span>Path: {{ source.file_path }}</span>
                </div>
              </div>
              <div class="card-stats">
                <div class="stat-item">
                  <el-icon><Document /></el-icon>
                  <span>{{ source.file_count }} files</span>
                </div>
                <div class="stat-item">
                  <el-icon><Collection /></el-icon>
                  <span>{{ source.version_count }} versions</span>
                </div>
                <div class="stat-item">
                  <el-icon><OfficeBuilding /></el-icon>
                  <span>{{ source.service_count }} services</span>
                </div>
              </div>
              <div class="card-services">
                <el-tag 
                  v-for="service in source.services.slice(0, 3)" 
                  :key="service"
                  size="small"
                  class="service-tag"
                >
                  {{ service }}
                </el-tag>
                <span v-if="source.services.length > 3" class="more-services">
                  +{{ source.services.length - 3 }} more
                </span>
              </div>
            </div>
          </el-card>
        </div>
      </div>
      
      <!-- No Results -->
      <div class="no-results" v-if="!loading && totalResults === 0">
        <el-empty description="No matching results found">
          <el-button type="primary" @click="clearSearch">Search Again</el-button>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Box, Document, Collection, OfficeBuilding, Files } from '@element-plus/icons-vue'
import { searchItems } from '@/api/search'

const router = useRouter()

// Reactive data
const searchQuery = ref('')
const searchType = ref('all')
const loading = ref(false)
const searchResults = ref({ jars: [], classes: [], jar_sources: [] })

// Computed properties
const showResults = computed(() => {
  return searchResults.value.jars.length > 0 || searchResults.value.classes.length > 0 || searchResults.value.jar_sources.length > 0
})

const jarResults = computed(() => searchResults.value.jars)
const classResults = computed(() => searchResults.value.classes)
const jarSourceResults = computed(() => searchResults.value.jar_sources)

const totalResults = computed(() => {
  return jarResults.value.length + classResults.value.length + jarSourceResults.value.length
})

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
    console.error('Search failed:', error)
    ElMessage.error('Search failed, please try again')
  } finally {
    loading.value = false
  }
}

const handleInputChange = () => {
  // Can add debounced search
}

const goToHistory = (type, name) => {
  router.push(`/history/${type}/${encodeURIComponent(name)}`)
}

const goToJarSource = (source) => {
  // Navigate to JAR history page
  router.push(`/history/jar/${encodeURIComponent(source.jar_name)}`)
}

const clearSearch = () => {
  searchQuery.value = ''
  searchResults.value = { jars: [], classes: [], jar_sources: [] }
}

// Watch search type changes
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

.card-info {
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 6px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #656d76;
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-item .el-icon {
  color: #409eff;
  flex-shrink: 0;
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

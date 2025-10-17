<template>
  <el-menu
    :default-active="activeIndex"
    class="nav-menu"
    mode="horizontal"
    @select="handleSelect"
    router
  >
    <el-menu-item index="/">
      <el-icon><Search /></el-icon>
      <span>Search</span>
    </el-menu-item>
    <el-menu-item index="/services">
      <el-icon><OfficeBuilding /></el-icon>
      <span>Services</span>
    </el-menu-item>
  </el-menu>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Search, OfficeBuilding } from '@element-plus/icons-vue'

const route = useRoute()

const activeIndex = computed(() => {
  return route.path
})

const handleSelect = (key) => {
  // Menu selection is handled by router
}
</script>

<style scoped>
.nav-menu {
  border-bottom: 1px solid #e4e7ed;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.nav-menu .el-menu-item {
  font-weight: 500;
}

.nav-menu .el-menu-item:hover {
  background-color: #f5f7fa;
}

.nav-menu .el-menu-item.is-active {
  color: #409eff;
  border-bottom-color: #409eff;
}
</style>

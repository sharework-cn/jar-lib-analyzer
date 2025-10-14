<template>
  <div class="github-diff-viewer">
    <!-- 文件头部信息 -->
    <div class="diff-header">
      <div class="file-info">
        <h4 class="file-path">{{ filePath }}</h4>
        <div class="file-stats">
          <span class="stat-item additions">+{{ additions }}</span>
          <span class="stat-item deletions">-{{ deletions }}</span>
          <span class="stat-item changes">{{ changePercentage }}%</span>
        </div>
      </div>
    </div>

    <!-- 差异内容 -->
    <div class="diff-content">
      <div 
        v-for="(hunk, hunkIndex) in hunks" 
        :key="hunkIndex" 
        class="diff-hunk"
      >
        <!-- 差异块头部 -->
        <div class="hunk-header">
          <span class="hunk-info">{{ hunk.header }}</span>
        </div>
        
        <!-- 差异行 -->
        <div class="hunk-lines">
          <div 
            v-for="(line, lineIndex) in hunk.lines" 
            :key="lineIndex"
            :class="[
              'diff-line',
              `diff-line--${line.type}`,
              { 'diff-line--highlight': line.highlight }
            ]"
          >
            <!-- 行号列 -->
            <div class="line-numbers">
              <span 
                v-if="line.old_line !== null" 
                class="line-number old-line"
              >
                {{ line.old_line }}
              </span>
              <span 
                v-if="line.new_line !== null" 
                class="line-number new-line"
              >
                {{ line.new_line }}
              </span>
            </div>
            
            <!-- 变更指示符 -->
            <div class="line-indicator">
              <span v-if="line.type === 'added'" class="indicator added">+</span>
              <span v-else-if="line.type === 'removed'" class="indicator removed">-</span>
              <span v-else class="indicator context"> </span>
            </div>
            
            <!-- 代码内容 -->
            <div class="line-content">
              <code class="code-line">{{ line.content }}</code>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  filePath: {
    type: String,
    required: true
  },
  hunks: {
    type: Array,
    required: true,
    default: () => []
  },
  additions: {
    type: Number,
    default: 0
  },
  deletions: {
    type: Number,
    default: 0
  },
  changePercentage: {
    type: Number,
    default: 0
  }
})

// 计算总变更行数
const totalChanges = computed(() => {
  return props.additions + props.deletions
})
</script>

<style scoped>
.github-diff-viewer {
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
  font-size: 12px;
  line-height: 1.45;
  overflow: hidden;
}

.diff-header {
  background: #f6f8fa;
  border-bottom: 1px solid #d0d7de;
  padding: 8px 16px;
}

.file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-path {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #24292f;
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
}

.file-stats {
  display: flex;
  gap: 8px;
  align-items: center;
}

.stat-item {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
}

.stat-item.additions {
  color: #1a7f37;
  background: #dafbe1;
}

.stat-item.deletions {
  color: #cf222e;
  background: #ffebe9;
}

.stat-item.changes {
  color: #656d76;
  background: #f3f4f6;
}

.diff-content {
  background: #ffffff;
}

.diff-hunk {
  border-bottom: 1px solid #d0d7de;
}

.diff-hunk:last-child {
  border-bottom: none;
}

.hunk-header {
  background: #f1f3f4;
  padding: 4px 16px;
  border-bottom: 1px solid #d0d7de;
}

.hunk-info {
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 11px;
  color: #656d76;
  background: #f1f3f4;
  padding: 2px 4px;
  border-radius: 3px;
}

.hunk-lines {
  background: #ffffff;
}

.diff-line {
  display: flex;
  align-items: stretch;
  min-height: 20px;
}

.diff-line--added {
  background: #f0fff4;
}

.diff-line--removed {
  background: #fff5f5;
}

.diff-line--context {
  background: #ffffff;
}

.diff-line--highlight {
  background: #fff8c5;
}

.line-numbers {
  display: flex;
  width: 80px;
  flex-shrink: 0;
  border-right: 1px solid #d0d7de;
  background: #f6f8fa;
}

.line-number {
  flex: 1;
  text-align: right;
  padding: 0 8px;
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 11px;
  color: #656d76;
  user-select: none;
  cursor: pointer;
  line-height: 20px;
}

.line-number:hover {
  color: #0969da;
}

.old-line {
  border-right: 1px solid #d0d7de;
}

.new-line {
  background: #f6f8fa;
}

.line-indicator {
  width: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-right: 1px solid #d0d7de;
  background: #f6f8fa;
}

.indicator {
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 12px;
  font-weight: bold;
  width: 12px;
  text-align: center;
  user-select: none;
}

.indicator.added {
  color: #1a7f37;
}

.indicator.removed {
  color: #cf222e;
}

.indicator.context {
  color: #656d76;
}

.line-content {
  flex: 1;
  padding: 0 8px;
  overflow-x: auto;
  background: inherit;
}

.code-line {
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 12px;
  line-height: 20px;
  white-space: pre;
  color: #24292f;
  background: transparent;
  border: none;
  padding: 0;
  margin: 0;
}

/* 语法高亮样式 */
.diff-line--added .code-line {
  color: #1a7f37;
}

.diff-line--removed .code-line {
  color: #cf222e;
}

.diff-line--context .code-line {
  color: #24292f;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .file-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .line-numbers {
    width: 60px;
  }
  
  .line-indicator {
    width: 16px;
  }
  
  .hunk-header {
    padding: 4px 8px;
  }
  
  .line-content {
    padding: 0 4px;
  }
}

/* 滚动条样式 */
.diff-content::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.diff-content::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.diff-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.diff-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>

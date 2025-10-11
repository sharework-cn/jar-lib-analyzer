<template>
  <div class="diff-viewer">
    <div class="diff-header">
      <h4>{{ filePath }}</h4>
      <div class="file-stats">
        <el-tag size="small" type="success">+{{ additions }}</el-tag>
        <el-tag size="small" type="danger">-{{ deletions }}</el-tag>
        <span class="change-percentage">{{ changePercentage }}%</span>
      </div>
    </div>
    
    <div class="diff-container">
      <div class="diff-panel">
        <div class="panel-header">
          <span class="version-label">版本 {{ fromVersion }}</span>
          <span class="file-size">{{ formatFileSize(sizeBefore) }}</span>
        </div>
        <div ref="fromEditor" class="editor-container"></div>
      </div>
      
      <div class="diff-panel">
        <div class="panel-header">
          <span class="version-label">版本 {{ toVersion }}</span>
          <span class="file-size">{{ formatFileSize(sizeAfter) }}</span>
        </div>
        <div ref="toEditor" class="editor-container"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { EditorView, basicSetup } from 'codemirror'
import { java } from '@codemirror/lang-java'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorState } from '@codemirror/state'
import { ViewUpdate } from '@codemirror/view'

const props = defineProps({
  filePath: String,
  fromVersion: Number,
  toVersion: Number,
  fromContent: String,
  toContent: String,
  additions: Number,
  deletions: Number,
  changePercentage: Number,
  sizeBefore: Number,
  sizeAfter: Number
})

const fromEditor = ref(null)
const toEditor = ref(null)
let fromEditorView = null
let toEditorView = null

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const createEditor = (container, content, isReadOnly = true) => {
  const state = EditorState.create({
    doc: content,
    extensions: [
      basicSetup,
      java(),
      oneDark,
      EditorView.editable.of(!isReadOnly),
      EditorView.theme({
        '&': {
          fontSize: '13px',
          fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace'
        },
        '.cm-content': {
          padding: '16px'
        },
        '.cm-focused': {
          outline: 'none'
        },
        '.cm-scroller': {
          fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace'
        }
      })
    ]
  })
  
  return new EditorView({
    state,
    parent: container
  })
}

const highlightDifferences = () => {
  if (!fromEditorView || !toEditorView) return
  
  const fromContent = fromEditorView.state.doc.toString()
  const toContent = toEditorView.state.doc.toString()
  
  // 简单的差异高亮实现
  // 这里可以添加更复杂的差异高亮逻辑
}

onMounted(() => {
  if (fromEditor.value && toEditor.value) {
    fromEditorView = createEditor(fromEditor.value, props.fromContent || '')
    toEditorView = createEditor(toEditor.value, props.toContent || '')
    
    // 同步滚动
    const syncScroll = (sourceView, targetView) => {
      return EditorView.updateListener.of((update) => {
        if (update.scrollChanged) {
          const scrollTop = sourceView.scrollDOM.scrollTop
          targetView.scrollDOM.scrollTop = scrollTop
        }
      })
    }
    
    // 添加同步滚动监听器
    fromEditorView.dispatch({
      effects: fromEditorView.state.reconfigure([
        ...fromEditorView.state.facet(EditorView.scrollMargins),
        syncScroll(fromEditorView, toEditorView)
      ])
    })
    
    toEditorView.dispatch({
      effects: toEditorView.state.reconfigure([
        ...toEditorView.state.facet(EditorView.scrollMargins),
        syncScroll(toEditorView, fromEditorView)
      ])
    })
  }
})

onUnmounted(() => {
  if (fromEditorView) {
    fromEditorView.destroy()
  }
  if (toEditorView) {
    toEditorView.destroy()
  }
})

// 监听内容变化
watch(() => [props.fromContent, props.toContent], () => {
  if (fromEditorView && props.fromContent !== undefined) {
    const currentContent = fromEditorView.state.doc.toString()
    if (currentContent !== props.fromContent) {
      fromEditorView.dispatch({
        changes: {
          from: 0,
          to: fromEditorView.state.doc.length,
          insert: props.fromContent
        }
      })
    }
  }
  
  if (toEditorView && props.toContent !== undefined) {
    const currentContent = toEditorView.state.doc.toString()
    if (currentContent !== props.toContent) {
      toEditorView.dispatch({
        changes: {
          from: 0,
          to: toEditorView.state.doc.length,
          insert: props.toContent
        }
      })
    }
  }
})
</script>

<style scoped>
.diff-viewer {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}

.diff-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #f6f8fa;
  border-bottom: 1px solid #d0d7de;
}

.diff-header h4 {
  margin: 0;
  font-family: monospace;
  color: #212529;
}

.file-stats {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.change-percentage {
  font-size: 0.875rem;
  color: #6c757d;
}

.diff-container {
  display: flex;
  height: 600px;
}

.diff-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #d0d7de;
}

.diff-panel:last-child {
  border-right: none;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  background: #f1f3f4;
  border-bottom: 1px solid #d0d7de;
  font-size: 0.875rem;
}

.version-label {
  font-weight: 600;
  color: #495057;
}

.file-size {
  color: #6c757d;
}

.editor-container {
  flex: 1;
  overflow: hidden;
}

:deep(.cm-editor) {
  height: 100%;
}

:deep(.cm-scroller) {
  height: 100%;
}

:deep(.cm-content) {
  padding: 16px;
  line-height: 1.4;
}

:deep(.cm-focused) {
  outline: none;
}

:deep(.cm-line) {
  padding: 0;
}

:deep(.cm-lineNumbers) {
  background: #f6f8fa;
  border-right: 1px solid #d0d7de;
}

:deep(.cm-lineNumbers .cm-gutterElement) {
  padding: 0 8px;
  color: #656d76;
  font-size: 12px;
}
</style>

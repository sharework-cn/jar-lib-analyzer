<template>
  <div class="diff2html-wrapper" ref="container"></div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { html as diff2html } from 'diff2html'
import 'diff2html/bundles/css/diff2html.min.css'
import hljs from 'highlight.js'

const props = defineProps({
  unifiedDiff: { type: String, required: true },
  filePath: { type: String, default: '' },
  drawFileList: { type: Boolean, default: false },
  matching: { type: String, default: 'lines' } // none, lines, words
})

const container = ref(null)

const render = () => {
  if (!container.value) return
  const html = diff2html(props.unifiedDiff || '', {
    inputFormat: 'diff',
    showFiles: props.drawFileList,
    matching: props.matching,
    drawFileList: props.drawFileList,
    outputFormat: 'line-by-line', // 单窗格统一风格
    renderNothingWhenEmpty: true
  })
  container.value.innerHTML = html
  // 语法高亮
  container.value.querySelectorAll('pre code').forEach((el) => hljs.highlightElement(el))
}

onMounted(render)
watch(() => props.unifiedDiff, render)

onBeforeUnmount(() => {
  if (container.value) container.value.innerHTML = ''
})
</script>

<style scoped>
.diff2html-wrapper {
  width: 100%;
}
</style>

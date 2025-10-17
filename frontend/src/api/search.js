import axios from 'axios'

const API_BASE_URL = ''

// 搜索JAR和Class文件
export async function searchItems(query, type = 'all') {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/search`, {
      params: {
        q: query,
        type: type
      }
    })
    return response.data
  } catch (error) {
    console.error('搜索失败:', error)
    throw error
  }
}

// 获取JAR文件版本历史
export async function getJarVersions(jarName) {
  try {
    const response = await axios.get(`${API_BASE_URL}/jars/${encodeURIComponent(jarName)}/versions`)
    return response.data
  } catch (error) {
    console.error('获取JAR版本历史失败:', error)
    throw error
  }
}

// 获取Class文件版本历史
export async function getClassVersions(className) {
  try {
    const response = await axios.get(`${API_BASE_URL}/classes/${encodeURIComponent(className)}/versions`)
    return response.data
  } catch (error) {
    console.error('获取Class版本历史失败:', error)
    throw error
  }
}

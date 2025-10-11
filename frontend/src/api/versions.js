import axios from 'axios'

const API_BASE_URL = '/api'

// 获取版本历史
export async function getVersionHistory(type, name) {
  try {
    const endpoint = type === 'jar' ? 'jars' : 'classes'
    const response = await axios.get(`${API_BASE_URL}/${endpoint}/${encodeURIComponent(name)}/versions`)
    return response.data
  } catch (error) {
    console.error('获取版本历史失败:', error)
    throw error
  }
}

// 获取版本详情
export async function getVersionDetails(type, name, versionNo) {
  try {
    const endpoint = type === 'jar' ? 'jars' : 'classes'
    const response = await axios.get(`${API_BASE_URL}/${endpoint}/${encodeURIComponent(name)}/versions/${versionNo}`)
    return response.data
  } catch (error) {
    console.error('获取版本详情失败:', error)
    throw error
  }
}

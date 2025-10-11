import axios from 'axios'

const API_BASE_URL = '/api'

// 获取版本差异
export async function getVersionDiff(type, name, fromVersion, toVersion, filePath = null) {
  try {
    const endpoint = type === 'jar' ? 'jars' : 'classes'
    const params = {
      from_version: fromVersion,
      to_version: toVersion
    }
    
    if (filePath) {
      params.file_path = filePath
    }
    
    const response = await axios.get(`${API_BASE_URL}/${endpoint}/${encodeURIComponent(name)}/diff`, {
      params: params
    })
    return response.data
  } catch (error) {
    console.error('获取版本差异失败:', error)
    throw error
  }
}

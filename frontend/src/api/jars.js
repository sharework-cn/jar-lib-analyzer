import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

export const getJars = async (limit = 100, lastJarName = null) => {
  try {
    const params = { limit }
    if (lastJarName) {
      params.last_jar_name = lastJarName
    }
    const response = await axios.get(`${API_BASE_URL}/api/jars`, { params })
    return response.data
  } catch (error) {
    console.error('Failed to fetch JARs:', error)
    throw error
  }
}

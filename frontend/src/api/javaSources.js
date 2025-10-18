import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

export const getJavaSources = async (limit = 100, lastName = null) => {
  try {
    const params = { limit }
    if (lastName) {
      params.last_class_name = lastName
    }
    const response = await axios.get(`${API_BASE_URL}/api/java-sources`, { params })
    return response.data
  } catch (error) {
    console.error('Failed to fetch Java Sources:', error)
    throw error
  }
}

export const getJavaSourceDetails = async (classFullName) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/java-sources/${encodeURIComponent(classFullName)}/details`)
    return response.data
  } catch (error) {
    console.error('Failed to fetch Java Source details:', error)
    throw error
  }
}

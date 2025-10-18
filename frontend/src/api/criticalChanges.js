import axios from 'axios'

const API_BASE_URL = ''

export const getCriticalDifferences = async (type, identifier) => {
  if (type === 'service') {
    const response = await axios.get(`${API_BASE_URL}/api/services/${identifier}/critical-differences`)
    return response.data
  } else if (type === 'jar') {
    // For JAR, we need to implement a similar endpoint
    const response = await axios.get(`${API_BASE_URL}/api/jars/${encodeURIComponent(identifier)}/critical-differences`)
    return response.data
  } else {
    throw new Error('Invalid type parameter')
  }
}

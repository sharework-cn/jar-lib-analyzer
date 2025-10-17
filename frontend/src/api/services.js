import axios from 'axios'

const API_BASE_URL = ''

// Get all services
export const getServices = async () => {
  const response = await axios.get(`${API_BASE_URL}/api/services`)
  return response.data
}

// Get service detail with JAR and Class files
export const getServiceDetail = async (serviceId) => {
  const response = await axios.get(`${API_BASE_URL}/api/services/${serviceId}`)
  return response.data
}

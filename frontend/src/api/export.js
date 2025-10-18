import axios from 'axios'

const API_BASE_URL = '/api'

/**
 * Export service details as Markdown
 * @param {number} serviceId - Service ID
 * @returns {Promise<Object>} Export data with filename and content
 */
export const exportServiceDetails = async (serviceId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/services/${serviceId}/export`, {
      responseType: 'json'
    })
    return response.data
  } catch (error) {
    console.error('Failed to export service details:', error)
    throw error
  }
}

/**
 * Export JAR version history as Markdown
 * @param {string} jarName - JAR name
 * @returns {Promise<Object>} Export data with filename and content
 */
export const exportJarHistory = async (jarName) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/jars/${encodeURIComponent(jarName)}/export`, {
      responseType: 'json'
    })
    return response.data
  } catch (error) {
    console.error('Failed to export JAR history:', error)
    throw error
  }
}

/**
 * Download file from browser
 * @param {string} content - File content
 * @param {string} filename - File name
 * @param {string} contentType - MIME type
 */
export const downloadFile = (content, filename, contentType = 'text/markdown') => {
  const blob = new Blob([content], { type: contentType })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

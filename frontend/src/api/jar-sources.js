import axios from 'axios'

const API_BASE_URL = ''

// Get JAR source files for a specific version
export const getJarSourceFiles = async (jarName, versionNo) => {
  const response = await axios.get(`${API_BASE_URL}/api/jars/${encodeURIComponent(jarName)}/sources/${versionNo}`)
  return response.data
}

// Get specific JAR source file content
export const getJarSourceFileContent = async (jarName, versionNo, classFullName) => {
  const response = await axios.get(`${API_BASE_URL}/api/jars/${encodeURIComponent(jarName)}/sources/${versionNo}/content`, {
    params: { class_full_name: classFullName }
  })
  return response.data.content
}

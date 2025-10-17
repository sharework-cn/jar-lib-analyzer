import axios from 'axios'

const API_BASE_URL = ''

// Get JAR source files for a specific version
export const getJarSourceFiles = async (jarName, versionNo) => {
  const response = await axios.get(`${API_BASE_URL}/api/jars/${encodeURIComponent(jarName)}/sources/${versionNo}`)
  return response.data
}

// Get specific JAR source file content
export const getJarSourceFileContent = async (jarName, versionNo, filePath) => {
  const response = await axios.get(`${API_BASE_URL}/api/jars/${encodeURIComponent(jarName)}/sources/${versionNo}/content`, {
    params: { file_path: filePath }
  })
  return response.data.content
}

import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: BASE,
  timeout: 90_000,  // Agent pipeline can take ~20-40s
  headers: { 'Content-Type': 'application/json' },
})

/**
 * POST /query — Main intelligence endpoint
 * @param {string} question
 * @param {Array<{role: string, content: string}>} chatHistory
 * @returns {Promise<QueryResponse>}
 */
export async function queryAgent(question, chatHistory = []) {
  const { data } = await client.post('/query', { question, chat_history: chatHistory })
  return data
}

/**
 * GET /health — Health + data loaded check
 */
export async function getHealth() {
  const { data } = await client.get('/health')
  return data
}

/**
 * GET /dataset/info — Column names, campaigns, segments
 */
export async function getDatasetInfo() {
  const { data } = await client.get('/dataset/info')
  return data
}

/**
 * GET /suggestions — Example questions
 */
export async function getSuggestions() {
  const { data } = await client.get('/suggestions')
  return data
}
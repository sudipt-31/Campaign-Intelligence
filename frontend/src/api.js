import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''

const client = axios.create({
  baseURL: BASE,
  timeout: 150_000,  // Agent pipeline can take ~20-40s, increasing for complex queries
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

/**
 * POST /export — Export report as PPT or DOCX
 * @param {Object} payload 
 */
export async function exportReport(payload) {
  const response = await client.post('/export', payload, { responseType: 'blob' })
  return response.data
}
/**
 * GET /query/stream — SSE stream for live agent progress.
 * Returns an EventSource. Caller must close it when done.
 * 
 * @param {string} question
 * @param {function} onMessage  - called with each status line string
 * @param {function} onDone     - called when stream ends
 * @returns {EventSource}
 */
export function streamQuery(question, onMessage, onDone) {
  const base = import.meta.env.VITE_API_URL || ''
  const url = `${base}/query/stream?question=${encodeURIComponent(question)}`
  const es = new EventSource(url)

  es.onmessage = (e) => {
    if (e.data === '__DONE__') {
      es.close()
      if (onDone) onDone()
    } else {
      if (onMessage) onMessage(e.data)
    }
  }

  es.onerror = () => {
    es.close()
    if (onDone) onDone()
  }

  return es
}

/** 后端 API 封装 */

async function request(path, options = {}) {
  const resp = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    let detail = `请求失败（${resp.status}）`
    try {
      const data = await resp.json()
      if (data.detail) detail = data.detail
    } catch {
      /* 忽略非 JSON 响应 */
    }
    throw new Error(detail)
  }
  return resp.json()
}

/** 解析视频链接，返回标题/封面/清晰度列表等 */
export function parseVideo(url) {
  return request('/api/parse', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

/** 发起下载，返回任务对象（需轮询进度）
 *  meta.title / meta.thumbnail 来自解析结果，用于下载记录展示封面与标题
 *  meta.mode 为 'video'（默认，视频+音频）或 'audio'（仅提取音频）
 */
export function startDownload(url, formatId, meta = {}) {
  return request('/api/download', {
    method: 'POST',
    body: JSON.stringify({
      url,
      format_id: formatId,
      mode: meta.mode || 'video',
      title: meta.title || '',
      thumbnail: meta.thumbnail || '',
    }),
  })
}

/** 查询单个任务进度 */
export function getTask(taskId) {
  return request(`/api/tasks/${taskId}`)
}

/** 查询任务历史 */
export function listTasks() {
  return request('/api/tasks')
}

/** 下载完成文件的访问地址 */
export function fileUrl(taskId) {
  return `/api/files/${taskId}`
}

<template>
  <div class="container">
    <!-- 报告页面 -->
    <div v-if="isReportPage">
      <Report />
    </div>
    
    <!-- 主应用页面 -->
    <div v-else>
      <!-- 标签页切换 -->
    <div class="tabs">
      <button 
        :class="['tab', { active: activeTab === 'upload' }]" 
        @click="activeTab = 'upload'"
      >
        上传分析
      </button>
      <button 
        :class="['tab', { active: activeTab === 'history' }]" 
        @click="activeTab = 'history'; loadReports()"
      >
        历史记录
      </button>
    </div>

    <!-- 上传分析页面 -->
    <div v-if="activeTab === 'upload'" class="tab-content">
      <!-- 步骤1: 上传文件 -->
      <div v-if="step === 1" class="card">
        <h2>QQ群年度报告分析器</h2>
        <p>上传 <a href="https://github.com/shuakami/qq-chat-exporter">qq-chat-exporter</a> 导出的 JSON，系统将自动分析并生成年度报告</p>
        
        <!-- 重要提示 -->
        <div class="notice-box">
          <h3>⚠️ 重要提示</h3>
          <ul>
            <li><strong>开发中项目：</strong>本项目仍在开发阶段，可能会出现未知错误或不稳定情况。</li>
            <li><strong>演示站点限制：</strong>本站点仅供演示使用，设有较严格的限流设置。为获得更好体验，推荐前往 <a href="https://github.com/ZiHuixi/QQgroup-annual-report-analyzer" target="_blank">GitHub 仓库</a> 自行部署，或搭建类似网站供他人使用。</li>
            <li><strong>数据安全提醒：</strong>虽然本项目采用 AGPL-3.0 开源协议，但上传的聊天记录属于敏感数据，仍存在一定泄露风险。请根据实际情况谨慎使用，建议仅上传不包含隐私信息的数据。</li>
          </ul>
        </div>
        
        <div class="card" style="margin-top: 20px;">
          <h3>时间范围设置</h3>
          <div class="time-range-selector">
            <div class="time-input-group">
              <label>起始日期：</label>
              <input 
                type="date" 
                v-model="startDate" 
                placeholder="留空表示不限制"
              />
            </div>
            <div class="time-input-group">
              <label>结束日期：</label>
              <input 
                type="date" 
                v-model="endDate" 
                placeholder="留空表示不限制"
              />
            </div>
          </div>
          <p class="time-range-hint">💡 留空表示不限制该端时间，可以只设置起始或结束日期（建议直接在导出时设置时间范围）</p>
        </div>

        <div class="card" style="margin-top: 20px;">
          <h3>选词模式</h3>
          <div class="mode-selector">
            <label class="mode-option">
              <input type="radio" v-model="autoSelect" :value="false" />
              <div class="mode-content">
                <strong>🎯 手动选词</strong>
                <p>从热词列表中自己选择最能代表这一年的词汇</p>
              </div>
            </label>
            <label class="mode-option">
              <input type="radio" v-model="autoSelect" :value="true" />
              <div class="mode-content">
                <strong>{{ aiFeatures.ai_word_selection_enabled ? '🤖 AI自动选词' : '📋 默认前十个' }}</strong>
                <p>{{ aiFeatures.ai_word_selection_enabled ? 'AI自动选择前10个热词并生成报告' : '自动选择词频最高的前10个热词并生成报告' }}</p>
              </div>
            </label>
          </div>
        </div>

        <div class="flex" style="margin-top: 20px;">
          <input type="file" accept=".json" @change="onFileChange" />
          <button :disabled="loading || !file" @click="uploadAndAnalyze">
            {{ loading ? '⏳ 分析中...' : '开始分析' }}
          </button>
        </div>
        
        <div v-if="loading" class="progress-info">
          <p>{{ loadingMessage }}</p>
        </div>
      </div>

      <!-- 步骤2: 选择词汇 (仅手动模式) -->
      <div v-if="step === 2" class="card">
        <h2>步骤2: 选择年度热词</h2>
        <div class="info-box">
          <div class="badge">群聊：{{ currentReport.chat_name }}</div>
          <div class="badge">消息数：{{ currentReport.message_count }}</div>
          <div class="badge">可选词数：{{ currentReport.available_words?.length || 0 }}</div>
          <div class="badge success">已选择：{{ selectedWords.length }} 个</div>
        </div>

        <p style="margin-top: 15px;">
          从下面的热词列表中选择最能代表这一年的词汇（<strong style="color: #dc3545;">选择10个</strong>）
        </p>

        <!-- 词汇列表 -->
        <div class="word-list">
          <div 
            v-for="word in paginatedWords" 
            :key="word.word"
            :class="['word-list-item', { selected: isWordSelected(word.word) }]"
            @click="toggleWord(word.word)"
          >
            <div class="word-list-header">
              <div class="word-main-info">
                <span class="word-list-text">{{ word.word }}</span>
                <span class="word-list-freq">出现 {{ word.freq }} 次</span>
              </div>
              <div class="select-indicator">
                {{ isWordSelected(word.word) ? '✓ 已选' : '点击选择' }}
              </div>
            </div>
            
            <div class="word-contributors">
              <strong>使用最多：</strong>
              <span v-for="(contributor, idx) in word.contributors.slice(0, 3)" :key="idx">
                {{ contributor.name }}({{ contributor.count }}次){{ idx < Math.min(2, word.contributors.length - 1) ? '、' : '' }}
              </span>
            </div>
            
            <div class="word-samples" v-if="word.samples && word.samples.length > 0">
              <strong>例句：</strong>
              <div class="sample-item" v-for="(sample, idx) in word.samples.slice(0, 2)" :key="idx">
                "{{ sample }}"
              </div>
            </div>
          </div>
        </div>

        <!-- 分页控制 -->
        <div class="pagination" v-if="currentReport.available_words?.length > wordsPerPage">
          <button 
            :disabled="currentWordPage <= 1" 
            @click="currentWordPage--"
          >
            上一页
          </button>
          <span>第 {{ currentWordPage }} / {{ totalWordPages }} 页</span>
          <button 
            :disabled="currentWordPage >= totalWordPages" 
            @click="currentWordPage++"
          >
            下一页
          </button>
        </div>

        <div class="selected-summary" :class="{ 'warning': selectedWords.length !== 10 }">
          已选择 {{ selectedWords.length }} / 10 个词汇
          <span v-if="selectedWords.length < 10" style="color: #dc3545; margin-left: 10px;">
            （还需选择 {{ 10 - selectedWords.length }} 个）
          </span>
          <span v-else-if="selectedWords.length === 10" style="color: #28a745; margin-left: 10px;">
            ✓ 已满足要求
          </span>
        </div>

        <div class="flex" style="margin-top: 20px;">
          <button @click="step = 1; resetState()">返回</button>
          <button 
            :disabled="selectedWords.length !== 10 || loading" 
            @click="finalizeReport"
            class="primary"
          >
            {{ loading ? '生成中...' : '确认选择并生成报告' }}
          </button>
        </div>
      </div>

      <!-- 步骤3: 生成完成 -->
      <div v-if="step === 3" class="card">
        <h2>✅ 报告生成完成！</h2>
        <div class="success-box">
          <p>{{ finalResult.message || '您的年度报告已成功生成并保存到数据库' }}</p>
          
          <div class="info-box" style="margin-top: 15px;">
            <div class="badge">报告ID：{{ finalResult.report_id }}</div>
          </div>
          
          <div style="margin-top: 20px;">
            <p style="margin-bottom: 10px; font-weight: 500;">🎨 选择模板风格：</p>
            <div class="template-selector">
              <div 
                v-for="template in availableTemplates" 
                :key="template.id"
                :class="['template-option', { selected: selectedTemplate === template.id }]"
                @click="selectedTemplate = template.id"
              >
                <div class="template-name">{{ template.name }}</div>
                <div class="template-desc">{{ template.description }}</div>
              </div>
            </div>
            
            <p style="margin: 15px 0 10px 0; font-weight: 500;">📊 访问您的报告：</p>
            <div class="url-display">
              {{ getTemplateReportUrl(selectedTemplate) }}
            </div>
            <div class="flex" style="margin-top: 15px; gap: 10px;">
              <button @click="openTemplateReport(selectedTemplate)" class="primary">
                🔗 立即查看报告
              </button>
              <button @click="copyTemplateUrl(selectedTemplate)">
                📋 复制链接
              </button>
            </div>
          </div>

          <div class="flex" style="margin-top: 30px;">
            <button @click="step = 1; resetState()">创建新报告</button>
            <button @click="activeTab = 'history'; loadReports()" class="primary">
              查看所有报告
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 历史记录页面 -->
    <div v-if="activeTab === 'history'" class="tab-content">
      <div class="card">
        <h2>历史报告</h2>
        
        <div class="search-box">
          <input 
            v-model="searchQuery" 
            placeholder="搜索群聊名称..." 
            @keyup.enter="loadReports()"
          />
          <button @click="loadReports()">搜索</button>
        </div>

        <div v-if="loadingReports" class="loading">加载中...</div>

        <div v-else-if="reports.data && reports.data.length > 0" class="reports-list">
          <div v-for="report in reports.data" :key="report.id" class="report-item">
            <div class="report-header">
              <h3>{{ report.chat_name }}</h3>
              <span class="report-date">{{ formatDate(report.created_at) }}</span>
            </div>
            <div class="report-info">
              <span class="badge">消息数：{{ report.message_count }}</span>
              <span class="badge">报告ID：{{ report.report_id }}</span>
            </div>
            <div class="report-url">
              <code>{{ getReportUrl(report.report_id) }}</code>
            </div>
            <div class="report-actions">
              <button @click="openReport(report.report_id)" class="primary">查看报告</button>
              <button @click="copyReportUrl(report.report_id)">复制链接</button>
              <button @click="deleteReport(report.report_id)" class="danger">删除</button>
            </div>
          </div>

          <!-- 分页 -->
          <div class="pagination" v-if="reports.total > reports.page_size">
            <button 
              :disabled="reports.page <= 1" 
              @click="changePage(reports.page - 1)"
            >
              上一页
            </button>
            <span>第 {{ reports.page }} / {{ Math.ceil(reports.total / reports.page_size) }} 页</span>
            <button 
              :disabled="reports.page >= Math.ceil(reports.total / reports.page_size)" 
              @click="changePage(reports.page + 1)"
            >
              下一页
            </button>
          </div>
        </div>

        <div v-else class="empty-state">
          <p>暂无报告记录</p>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { reactive, ref, computed, onMounted } from 'vue'
import Report from './Report.vue'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const SITE_URL = window.location.origin

let csrfToken = null

// AI功能开关状态
const aiFeatures = ref({
  ai_comment_enabled: false,
  ai_word_selection_enabled: false
})

const fetchCsrfToken = async () => {
  try {
    const { data } = await axios.get(`${API_BASE}/csrf-token`)
    csrfToken = data.csrf_token
    console.log('✅ CSRF token已获取')
  } catch (err) {
    console.error('❌ 获取CSRF token失败:', err)
  }
}

// 获取AI功能开关状态
const fetchAIFeatures = async () => {
  try {
    const { data } = await axios.get(`${API_BASE}/health`)
    if (data.features) {
      aiFeatures.value = data.features
      console.log('✅ AI功能状态:', aiFeatures.value)
    }
  } catch (err) {
    console.error('❌ 获取AI功能状态失败:', err)
  }
}

// 配置axios请求拦截器，自动添加CSRF token
axios.interceptors.request.use(
  config => {
    // 对所有非GET请求添加CSRF token
    if (config.method && !['get', 'head', 'options'].includes(config.method.toLowerCase())) {
      if (csrfToken) {
        config.headers['X-CSRF-Token'] = csrfToken
      }
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 配置axios响应拦截器，处理CSRF错误
axios.interceptors.response.use(
  response => response,
  async error => {
    // 如果遇到CSRF验证失败，尝试重新获取token并重试
    if (error.response?.status === 403 && error.response?.data?.error?.includes('CSRF')) {
      console.warn('⚠️ CSRF token失效，正在重新获取...')
      await fetchCsrfToken()
      // 重试原始请求
      if (csrfToken) {
        error.config.headers['X-CSRF-Token'] = csrfToken
        return axios.request(error.config)
      }
    }
    return Promise.reject(error)
  }
)

// 状态管理
const activeTab = ref('upload')
const step = ref(1) // 1=上传, 2=选词, 3=完成
const file = ref(null)
const loading = ref(false)
const loadingMessage = ref('')
const loadingReports = ref(false)
const autoSelect = ref(false)  // 是否AI自动选词

// 时间范围设置
const startDate = ref('')
const endDate = ref('')

// 当前报告数据
const currentReport = ref(null)
const selectedWords = ref([])
const finalResult = ref({})
const aiComments = ref({})
const showAIComments = ref(false)

// 词汇选择分页
const currentWordPage = ref(1)
const wordsPerPage = 10

// 计算分页后的词汇列表
const paginatedWords = computed(() => {
  if (!currentReport.value?.available_words) return []
  const start = (currentWordPage.value - 1) * wordsPerPage
  const end = start + wordsPerPage
  return currentReport.value.available_words.slice(start, end)
})

// 计算总页数
const totalWordPages = computed(() => {
  if (!currentReport.value?.available_words) return 0
  return Math.ceil(currentReport.value.available_words.length / wordsPerPage)
})

// 历史报告
const reports = ref({ data: [], total: 0, page: 1, page_size: 20 })
const searchQuery = ref('')

// 模板相关
const availableTemplates = ref([])
const selectedTemplate = ref('classic')

// 加载可用模板列表
const loadTemplates = async () => {
  try {
    const { data } = await axios.get(`${API_BASE}/templates`)
    availableTemplates.value = data.templates || []
    if (availableTemplates.value.length > 0) {
      selectedTemplate.value = availableTemplates.value[0].id
    }
  } catch (err) {
    console.error('加载模板失败:', err)
    // 使用默认模板
    availableTemplates.value = [{
      id: 'classic',
      name: '模板1',
      description: '最初的模板'
    }]
  }
}

// 获取指定模板的报告URL
const getTemplateReportUrl = (templateId) => {
  if (!finalResult.value.report_id) return ''
  return `${SITE_URL}/report/${templateId}/${finalResult.value.report_id}`
}

// 打开指定模板的报告
const openTemplateReport = (templateId) => {
  if (!finalResult.value.report_id) return
  window.open(`/report/${templateId}/${finalResult.value.report_id}`, '_blank')
}

// 复制指定模板的URL
const copyTemplateUrl = async (templateId) => {
  const url = getTemplateReportUrl(templateId)
  try {
    await navigator.clipboard.writeText(url)
    alert('链接已复制到剪贴板')
  } catch (err) {
    prompt('请手动复制链接：', url)
  }
}


// 判断是否为报告页面
const isReportPage = computed(() => {
  return window.location.pathname.startsWith('/report/')
})

// 计算报告URL
const reportUrl = computed(() => {
  if (!finalResult.value.report_id) return ''
  return `${SITE_URL}/report/${finalResult.value.report_id}`
})

// 获取报告URL
const getReportUrl = (reportId) => {
  return `${SITE_URL}/report/${reportId}`
}

// 打开报告
const openReport = (reportId) => {
  window.open(`/report/${reportId}`, '_blank')
}

// 复制报告URL
const copyReportUrl = async (reportId) => {
  const url = getReportUrl(reportId)
  try {
    await navigator.clipboard.writeText(url)
    alert('链接已复制到剪贴板')
  } catch (err) {
    prompt('请手动复制链接：', url)
  }
}

// 文件选择
const onFileChange = (e) => {
  const [f] = e.target.files || []
  file.value = f || null
}

// 重置状态
const resetState = () => {
  file.value = null
  currentReport.value = null
  selectedWords.value = []
  finalResult.value = {}
  aiComments.value = {}
  showAIComments.value = false
  loadingMessage.value = ''
  currentWordPage.value = 1
}

// 计算动态超时时间
const calculateTimeout = (fileSize, useAI) => {
  // 基础超时: 60秒
  const baseTimeout = 60
  
  // 文件大小因素: 每MB增加0.5秒
  const fileSizeMB = fileSize / (1024 * 1024)
  const fileSizeTimeout = Math.ceil(fileSizeMB * 0.5)
  
  // AI因素: 使用AI额外增加90秒（选词+评论需要更多时间）
  const aiTimeout = useAI ? 90 : 0
  
  // 计算总超时时间（秒）
  let totalTimeout = baseTimeout + fileSizeTimeout + aiTimeout
  
  // 设置最小值120秒，最大值600秒（10分钟）
  totalTimeout = Math.max(120, Math.min(totalTimeout, 600))
  
  return totalTimeout * 1000 // 转换为毫秒
}

// 步骤1-3: 上传并分析
const uploadAndAnalyze = async () => {
  if (!file.value) return
  loading.value = true
  
  // 计算动态超时时间
  const timeoutMs = calculateTimeout(file.value.size, autoSelect.value)
  const timeoutSeconds = Math.ceil(timeoutMs / 1000)
  
  // 根据AI功能开关状态设置加载提示
  if (autoSelect.value) {
    if (aiFeatures.value.ai_word_selection_enabled && aiFeatures.value.ai_comment_enabled) {
      loadingMessage.value = `正在上传并分析，AI将自动选词并生成报告（AI锐评中）...\n（预计最多需要 ${timeoutSeconds} 秒）`
    } else if (aiFeatures.value.ai_word_selection_enabled) {
      loadingMessage.value = `正在上传并分析，AI将自动选词并生成报告...\n（预计最多需要 ${timeoutSeconds} 秒）`
    } else if (aiFeatures.value.ai_comment_enabled) {
      loadingMessage.value = `正在上传并分析，将自动选择前10个热词并生成报告（AI锐评中）...\n（预计最多需要 ${timeoutSeconds} 秒）`
    } else {
      loadingMessage.value = `正在上传并分析，将自动选择前10个热词并生成报告...\n（预计最多需要 ${timeoutSeconds} 秒）`
    }
  } else {
    loadingMessage.value = `正在上传并分析，请稍候...\n（预计最多需要 ${timeoutSeconds} 秒）`
  }
  
  console.log(`📊 文件大小: ${(file.value.size / (1024 * 1024)).toFixed(2)} MB`)
  console.log(`🤖 使用AI: ${autoSelect.value ? '是' : '否'}`)
  console.log(`⏱️ 超时设置: ${timeoutSeconds} 秒`)
  
  try {
    const form = new FormData()
    form.append('file', file.value)
    form.append('auto_select', autoSelect.value ? 'true' : 'false')
    
    // 添加时间范围参数
    if (startDate.value) {
      form.append('start_date', startDate.value)
      console.log(`📅 起始日期: ${startDate.value}`)
    }
    if (endDate.value) {
      form.append('end_date', endDate.value)
      console.log(`📅 结束日期: ${endDate.value}`)
    }
    
    const { data } = await axios.post(`${API_BASE}/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: timeoutMs
    })
    
    if (data.error) throw new Error(data.error)
    
    // AI自动模式：直接显示结果
    if (autoSelect.value && data.success) {
    finalResult.value = data
    // 加载AI评论
      try {
        const detailRes = await axios.get(`${API_BASE}/reports/${data.report_id}`)
        aiComments.value = detailRes.data.ai_comments || {}
        showAIComments.value = true
      } catch (e) {
        console.error('加载AI评论失败:', e)
      }
      step.value = 3
    } else {
      // 手动模式：进入选词页面
      currentReport.value = data
      step.value = 2
    }
  } catch (err) {
    const respErr = err?.response?.data?.error
    const msg = respErr ? `分析失败: ${respErr}` : `分析失败: ${err.message || '未知错误'}`
    alert(msg)
  } finally {
    loading.value = false
    loadingMessage.value = ''
  }
}

// 词汇选择
const isWordSelected = (word) => {
  return selectedWords.value.includes(word)
}

const toggleWord = (word) => {
  const index = selectedWords.value.indexOf(word)
  if (index > -1) {
    selectedWords.value.splice(index, 1)
  } else {
    // 限制最多选择10个词
    if (selectedWords.value.length >= 10) {
      alert('最多只能选择10个词汇')
      return
    }
    selectedWords.value.push(word)
  }
}

// 步骤4-6: 最终化报告（手动选词后）
const finalizeReport = async () => {
  if (selectedWords.value.length !== 10) {
    alert('必须选择正好10个词汇才能继续')
    return
  }
  
  loading.value = true
  
  // 根据AI锐评开关设置加载提示
  if (aiFeatures.value.ai_comment_enabled) {
    loadingMessage.value = '正在生成报告（AI锐评中）...'
  } else {
    loadingMessage.value = '正在生成报告...'
  }
  
  // finalize阶段主要是AI评论生成，设置固定超时180秒（3分钟）
  const finalizeTimeout = 180 * 1000
  console.log('⏱️ Finalize超时设置: 180 秒（AI评论生成）')
  
  try {
    // 按词频排序选中的词（从高到低）
    const wordFreqMap = {}
    currentReport.value.available_words.forEach(w => {
      wordFreqMap[w.word] = w.freq
    })
    const sortedWords = [...selectedWords.value].sort((a, b) => {
      return (wordFreqMap[b] || 0) - (wordFreqMap[a] || 0)
    })
    
    const { data } = await axios.post(`${API_BASE}/finalize`, {
      report_id: currentReport.value.report_id,
      selected_words: sortedWords,
      oss_key: currentReport.value.oss_key
    }, {
      timeout: finalizeTimeout
    })
    
    if (data.error) throw new Error(data.error)
    
    finalResult.value = data
    
    // 加载AI评论
    try {
      const detailRes = await axios.get(`${API_BASE}/reports/${data.report_id}`)
      aiComments.value = detailRes.data.ai_comments || {}
      showAIComments.value = true
    } catch (e) {
      console.error('加载AI评论失败:', e)
    }
    
    step.value = 3
  } catch (err) {
    const respErr = err?.response?.data?.error
    const msg = respErr ? `生成失败: ${respErr}` : `生成失败: ${err.message || '未知错误'}`
    alert(msg)
  } finally {
    loading.value = false
    loadingMessage.value = ''
  }
}

// 加载报告列表（后端已按user_id过滤，直接使用）
const loadReports = async (page = 1) => {
  loadingReports.value = true
  try {
    const params = { page, page_size: 20 }
    if (searchQuery.value) {
      params.chat_name = searchQuery.value
    }
    
    const { data } = await axios.get(`${API_BASE}/reports`, { params })
    reports.value = data
  } catch (err) {
    alert('加载失败: ' + (err.message || '未知错误'))
  } finally {
    loadingReports.value = false
  }
}

const changePage = (page) => {
  loadReports(page)
}

const deleteReport = async (reportId) => {
  if (!confirm('确定要删除这个报告吗？此操作不可恢复！')) return
  
  try {
    await axios.delete(`${API_BASE}/reports/${reportId}`)
    alert('删除成功')
    loadReports(reports.value.page)
  } catch (err) {
    const errorMsg = err?.response?.data?.error || '删除失败，请稍后重试'
    alert(errorMsg)
  }
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Shanghai'
  })
}

// 页面加载时初始化
onMounted(async () => {
  await fetchCsrfToken()
  await fetchAIFeatures()
  loadTemplates()
})
</script>

<style scoped>
/* 标签页样式 */
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 30px;
  padding: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.2);
}

.tab {
  flex: 1;
  padding: 14px 24px;
  background: rgba(255, 255, 255, 0.1);
  border: 2px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
}

.tab:hover {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  transform: translateY(-2px);
}

.tab.active {
  background: white;
  color: #667eea;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.tab-content {
  animation: fadeIn 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes fadeIn {
  from { 
    opacity: 0; 
    transform: translateY(20px);
  }
  to { 
    opacity: 1; 
    transform: translateY(0);
  }
}

/* 模式选择器 */
.mode-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 15px;
}

.mode-option {
  display: flex;
  align-items: flex-start;
  padding: 20px;
  border: 3px solid #e8eaf6;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
  position: relative;
  overflow: hidden;
}

.mode-option::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  opacity: 0;
  transition: opacity 0.4s;
  z-index: 0;
}

.mode-option:hover {
  border-color: #667eea;
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.25);
}

.mode-option:hover::before {
  opacity: 0.05;
}

.mode-option input[type="radio"] {
  margin-right: 12px;
  margin-top: 3px;
  width: 20px;
  height: 20px;
  cursor: pointer;
  position: relative;
  z-index: 1;
}

.mode-option input[type="radio"]:checked + .mode-content {
  color: #667eea;
}

.mode-option input[type="radio"]:checked ~ * {
  position: relative;
  z-index: 1;
}

.mode-content {
  position: relative;
  z-index: 1;
}

.mode-content p {
  margin: 8px 0 0 0;
  font-size: 14px;
  color: #666;
  line-height: 1.6;
}

.mode-content strong {
  font-size: 16px;
  display: block;
  margin-bottom: 4px;
}

/* 进度信息 */
.progress-info {
  margin-top: 20px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  text-align: center;
  color: white;
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); }
}

.info-box {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  padding: 15px;
  background: linear-gradient(135deg, #f8f9ff 0%, #e8eaf6 100%);
  border-radius: 12px;
  border: 2px solid #e8eaf6;
}

/* 词汇列表样式 */
.word-list {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 时间范围选择器样式 */
.time-range-selector {
  display: flex;
  gap: 20px;
  margin-top: 15px;
}

.time-input-group {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.time-input-group label {
  font-weight: 700;
  color: #333;
  margin-bottom: 8px;
  font-size: 16px;
}

.time-input-group input[type="date"] {
  padding: 12px 16px;
  border: 2px solid #cbd5e1;
  border-radius: 12px;
  font-size: 16px;
  color: #444;
  background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
  transition: all 0.3s ease;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
}

.time-input-group input[type="date"]::placeholder {
  color: #aaa;
  font-style: italic;
}

.time-input-group input[type="date"]:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 12px rgba(102, 126, 234, 0.7);
}

.word-list-item {
  padding: 20px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
  border: 3px solid #e8eaf6;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.word-list-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  opacity: 0;
  transition: opacity 0.4s;
}

.word-list-item:hover {
  border-color: #667eea;
  transform: translateX(8px);
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.25);
}

.word-list-item:hover::before {
  opacity: 0.05;
}

.word-list-item.selected {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #667eea;
  color: white;
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.4);
  transform: translateX(8px) scale(1.02);
}

.word-list-item.selected .word-list-text,
.word-list-item.selected .word-list-freq,
.word-list-item.selected .word-contributors,
.word-list-item.selected .word-samples strong,
.word-list-item.selected .sample-item {
  color: white;
}

.word-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  position: relative;
  z-index: 1;
}

.word-main-info {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.word-list-text {
  font-size: 20px;
  font-weight: 700;
  color: #333;
  letter-spacing: 0.5px;
}

.word-list-item.selected .word-list-text {
  color: white;
}

.word-list-freq {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.word-list-item.selected .word-list-freq {
  color: rgba(255, 255, 255, 0.9);
}

.select-indicator {
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  background: linear-gradient(135deg, #f8f9ff 0%, #e8eaf6 100%);
  color: #667eea;
  border: 2px solid #e8eaf6;
  transition: all 0.3s;
}

.word-list-item.selected .select-indicator {
  background: rgba(255, 255, 255, 0.25);
  color: white;
  border-color: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(10px);
}

.word-contributors {
  margin-bottom: 10px;
  font-size: 14px;
  color: #555;
  position: relative;
  z-index: 1;
  line-height: 1.6;
}

.word-list-item.selected .word-contributors {
  color: rgba(255, 255, 255, 0.95);
}

.word-contributors strong {
  color: #333;
  margin-right: 6px;
  font-weight: 600;
}

.word-list-item.selected .word-contributors strong {
  color: white;
}

.word-samples {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 2px solid #e8eaf6;
  position: relative;
  z-index: 1;
}

.word-list-item.selected .word-samples {
  border-top-color: rgba(255, 255, 255, 0.3);
}

.word-samples strong {
  display: block;
  margin-bottom: 8px;
  color: #333;
  font-size: 14px;
  font-weight: 600;
}

.word-list-item.selected .word-samples strong {
  color: white;
}

.sample-item {
  margin: 6px 0;
  padding: 10px 14px;
  background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
  border-left: 4px solid #667eea;
  border-radius: 8px;
  font-size: 13px;
  color: #555;
  line-height: 1.6;
  transition: all 0.3s;
}

.word-list-item.selected .sample-item {
  background: rgba(255, 255, 255, 0.2);
  border-left-color: white;
  color: white;
  backdrop-filter: blur(10px);
}

.badge {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  transition: all 0.3s;
}

.badge:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

.badge.success {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  box-shadow: 0 4px 12px rgba(56, 239, 125, 0.3);
}

.badge.success:hover {
  box-shadow: 0 6px 16px rgba(56, 239, 125, 0.4);
}

/* 标题和文本美化 */
h2 {
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 16px;
  letter-spacing: 0.5px;
}

h3 {
  font-size: 20px;
  font-weight: 700;
  color: #333;
  margin-bottom: 12px;
  letter-spacing: 0.3px;
}

p {
  font-size: 15px;
  line-height: 1.8;
  color: #555;
}

.time-range-hint {
  margin-top: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #fff9e6 0%, #fffbf0 100%);
  border-left: 4px solid #ffc107;
  border-radius: 8px;
  color: #856404;
  font-size: 14px;
  font-weight: 500;
}

/* 文件上传输入框美化 */
input[type="file"] {
  padding: 14px 20px;
  border: 3px dashed #e8eaf6;
  border-radius: 12px;
  background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
  cursor: pointer;
  transition: all 0.3s;
  font-size: 15px;
  color: #555;
  font-weight: 500;
}

input[type="file"]:hover {
  border-color: #667eea;
  background: linear-gradient(135deg, #ffffff 0%, #f0f2ff 100%);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
}

input[type="file"]::file-selector-button {
  padding: 10px 20px;
  margin-right: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s;
}

input[type="file"]::file-selector-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

/* 通知框美化 */
.notice-box {
  padding: 24px;
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
  border-left: 5px solid #f5576c;
  border-radius: 12px;
  margin: 20px 0;
  box-shadow: 0 4px 16px rgba(245, 87, 108, 0.1);
}

.notice-box h3 {
  color: #c82333;
  margin-bottom: 16px;
  font-size: 18px;
}

.notice-box ul {
  margin: 0;
  padding-left: 24px;
}

.notice-box li {
  margin: 10px 0;
  line-height: 1.8;
  color: #721c24;
}

.notice-box strong {
  color: #c82333;
  font-weight: 700;
}

.notice-box a {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s;
}

.notice-box a:hover {
  color: #764ba2;
  text-decoration: underline;
}

/* 保留旧的网格样式以备用 */
.word-selector {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
  margin-top: 15px;
  max-height: 400px;
  overflow-y: auto;
  padding: 10px;
  background: #f9f9f9;
  border-radius: 8px;
}

.word-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.word-item:hover {
  border-color: #007bff;
  box-shadow: 0 2px 8px rgba(0,123,255,0.2);
}

.word-item.selected {
  background: #007bff;
  color: white;
  border-color: #0056b3;
}

.word-text {
  font-weight: 500;
}

.word-freq {
  font-size: 12px;
  opacity: 0.7;
}

.selected-summary {
  margin-top: 20px;
  padding: 16px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  text-align: center;
  font-weight: 600;
  font-size: 16px;
  color: white;
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
  transition: all 0.4s;
}

.selected-summary:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.4);
}

.selected-summary.warning {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  box-shadow: 0 8px 32px rgba(245, 87, 108, 0.3);
}

.selected-summary.warning:hover {
  box-shadow: 0 12px 40px rgba(245, 87, 108, 0.4);
}

.success-box {
  padding: 30px;
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  border-radius: 20px;
  box-shadow: 0 12px 48px rgba(56, 239, 125, 0.3);
  color: white;
}

.success-box h2 {
  color: white;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.success-box p {
  color: white;
  font-size: 16px;
  line-height: 1.6;
}

.url-display {
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.95);
  border: 3px solid rgba(255, 255, 255, 0.5);
  border-radius: 12px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  color: #667eea;
  word-break: break-all;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.ai-comments-section {
  margin-top: 25px;
  padding-top: 20px;
  border-top: 2px solid #c3e6cb;
}

.ai-comments-section h3 {
  margin: 0 0 15px 0;
  color: #155724;
}

.ai-comment-box {
  background: white;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #c3e6cb;
}

.comment-section {
  margin-bottom: 15px;
}

.comment-section:last-child {
  margin-bottom: 0;
}

.comment-section h4 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #155724;
}

.comment-section p {
  margin: 5px 0;
  line-height: 1.6;
}

.comment-section ul {
  margin: 5px 0;
  padding-left: 20px;
}

.comment-section li {
  margin: 5px 0;
  line-height: 1.6;
}

.search-box {
  display: flex;
  gap: 12px;
  margin-bottom: 25px;
}

.search-box input {
  flex: 1;
  padding: 14px 20px;
  border: 3px solid #e8eaf6;
  border-radius: 12px;
  font-size: 15px;
  transition: all 0.3s;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
}

.search-box input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.2);
  transform: translateY(-2px);
}

.reports-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.report-item {
  padding: 25px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
  border-radius: 16px;
  border: 3px solid #e8eaf6;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.report-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  opacity: 0;
  transition: opacity 0.4s;
}

.report-item:hover {
  border-color: #667eea;
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.25);
}

.report-item:hover::before {
  opacity: 0.05;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  position: relative;
  z-index: 1;
}

.report-header h3 {
  margin: 0;
  color: #333;
  font-size: 20px;
  font-weight: 700;
}

.report-date {
  color: #666;
  font-size: 14px;
  font-weight: 500;
  padding: 6px 12px;
  background: linear-gradient(135deg, #f8f9ff 0%, #e8eaf6 100%);
  border-radius: 20px;
}

.report-info {
  display: flex;
  gap: 12px;
  margin-bottom: 15px;
  flex-wrap: wrap;
  position: relative;
  z-index: 1;
}

.report-url {
  margin: 15px 0;
  padding: 14px 18px;
  background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
  border-radius: 12px;
  border: 2px solid #e8eaf6;
  position: relative;
  z-index: 1;
}

.report-url code {
  font-size: 13px;
  color: #667eea;
  word-break: break-all;
  font-weight: 600;
}

.report-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
  position: relative;
  z-index: 1;
}

.report-actions button {
  padding: 12px 24px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 12px;
  transition: all 0.3s;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin-top: 30px;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9ff 0%, #e8eaf6 100%);
  border-radius: 16px;
}

.pagination button {
  padding: 12px 24px;
  font-weight: 600;
  border-radius: 12px;
  transition: all 0.3s;
}

.pagination span {
  font-weight: 600;
  color: #667eea;
  font-size: 15px;
}

.empty-state {
  text-align: center;
  padding: 60px 40px;
  color: #999;
  font-size: 16px;
  background: linear-gradient(135deg, #f8f9ff 0%, #e8eaf6 100%);
  border-radius: 16px;
  border: 3px dashed #e8eaf6;
}

.loading {
  text-align: center;
  padding: 60px 40px;
  color: #667eea;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #f8f9ff 0%, #e8eaf6 100%);
  border-radius: 16px;
  animation: pulse 2s ease-in-out infinite;
}

button {
  padding: 12px 24px;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: linear-gradient(135deg, #f8f9ff 0%, #e8eaf6 100%);
  color: #667eea;
  border: 2px solid #e8eaf6;
}

button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.2);
  border-color: #667eea;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

button.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3);
}

button.primary:hover:not(:disabled) {
  box-shadow: 0 12px 32px rgba(102, 126, 234, 0.4);
  transform: translateY(-3px);
}

button.danger {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  border-color: transparent;
  box-shadow: 0 8px 24px rgba(245, 87, 108, 0.3);
}

button.danger:hover:not(:disabled) {
  box-shadow: 0 12px 32px rgba(245, 87, 108, 0.4);
  transform: translateY(-3px);
}

/* 模板选择器样式 */
.template-selector {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 20px;
  margin-top: 15px;
}

.template-option {
  padding: 20px;
  background: rgba(255, 255, 255, 0.95);
  border: 3px solid rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
}

.template-option::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.3) 0%, rgba(255, 255, 255, 0.1) 100%);
  opacity: 0;
  transition: opacity 0.4s;
}

.template-option:hover {
  border-color: rgba(255, 255, 255, 0.8);
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

.template-option:hover::before {
  opacity: 1;
}

.template-option.selected {
  background: rgba(255, 255, 255, 1);
  border-color: white;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
  transform: translateY(-6px) scale(1.02);
}

.template-name {
  font-size: 18px;
  font-weight: 700;
  color: #155724;
  margin-bottom: 8px;
  position: relative;
  z-index: 1;
}

.template-desc {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.7);
  line-height: 1.6;
  position: relative;
  z-index: 1;
}
</style>

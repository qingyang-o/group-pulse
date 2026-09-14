<template>
  <div class="report-page-wrapper classic-template">
    <div class="report-container" v-if="report">
      <div class="stripe"></div>
      
      <!-- 头部 -->
      <div class="header">
        <img class="header-decor" :src="decorFairy" alt="装饰">
        <div class="header-badge">Annual Report</div>
        <div class="header-star-group">★ ★ ★</div>
        <h1 :class="getTitleClass(report.chat_name)">{{ report.chat_name }}</h1>
        <div class="subtitle">年度报告</div>
        <div class="header-stats">
          <div class="stat-box">
            <div class="stat-value">{{ formatNumber(report.message_count) }}</div>
            <div class="stat-label">消息总数</div>
          </div>
        </div>
      </div>
      
      <div class="stripe-diagonal"></div>
      
      <!-- 柱状图 -->
      <div class="chart-section">
        <div class="section-header">
          <div class="section-title">热词榜</div>
        </div>
        
        <div class="bar-chart">
          <div v-for="(word, index) in report.selected_words" :key="word.word" class="bar-item">
            <div class="bar-value">{{ word.freq }}</div>
            <div class="bar-wrapper">
              <div class="bar" :style="{ height: word.bar_height + '%' }">
                <div v-for="(seg, segIndex) in word.segments" :key="segIndex"
                     class="bar-segment" 
                     :style="{ height: seg.percent + '%', backgroundColor: seg.color }">
                </div>
              </div>
            </div>
            <div class="bar-label">{{ word.word }}</div>
            <div class="bar-rank">#{{ index + 1 }}</div>
            <div class="bar-contributors">
              <div v-for="(item, itemIndex) in word.legend" :key="itemIndex"
                   :class="['bar-contributor-item', { empty: !item.name }]">
                <div class="bar-contributor-dot" :style="{ background: item.color }"></div>
                <span class="bar-contributor-name">{{ item.name }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="divider">
        <div class="divider-line"></div>
      </div>
      
      <!-- 热词卡片 -->
      <div class="section">
        <div class="section-header">
          <div class="section-title">热词档案</div>
        </div>
        
        <div class="word-cards">
          <div v-for="(word, index) in report.selected_words" :key="word.word" 
               :class="['word-card', `color-${index + 1}`]">
            <div class="word-card-header">
              <div class="word-card-left">
                <div class="word-card-rank">#{{ index + 1 }}</div>
                <div class="word-card-title">{{ word.word }}</div>
              </div>
              <div class="word-card-freq">{{ word.freq }}次</div>
            </div>
            
            <div v-if="word.ai_comment" class="word-card-comment">{{ word.ai_comment }}</div>
            
            <div class="word-card-contributors">
              {{ word.contributors_text }}
            </div>
            
            <ul class="word-card-samples">
              <li v-for="(sample, sampleIndex) in word.samples.slice(0, 3)" :key="sampleIndex">
                {{ truncateText(sample, 40) }}
              </li>
            </ul>
          </div>
        </div>
      </div>
      
      <div class="stripe"></div>
      
      <!-- 榜单 -->
      <div class="section rankings-section">
        <div class="section-header">
          <div class="section-title">荣誉殿堂</div>
        </div>
        
        <div class="rankings-grid">
          <div v-for="ranking in report.rankings" :key="ranking.title" class="ranking-card">
            <div class="ranking-card-header">
              {{ ranking.icon }} {{ ranking.title }}
            </div>
            
            <div v-if="ranking.first" class="ranking-first">
              <div class="ranking-first-crown">👑</div>
              <img class="ranking-first-avatar" 
                   :src="ranking.first.avatar" 
                   :alt="ranking.first.name"
                   @error="handleImageError">
              <div class="ranking-first-name">{{ ranking.first.name }}</div>
              <div class="ranking-first-value">{{ ranking.first.value }}{{ ranking.unit }}</div>
            </div>
            
            <div v-if="ranking.others" class="ranking-others">
              <div v-for="(item, itemIndex) in ranking.others" :key="itemIndex" class="ranking-item">
                <div class="ranking-item-pos">{{ itemIndex + 2 }}</div>
                <img class="ranking-item-avatar" 
                     :src="item.avatar" 
                     :alt="item.name"
                     @error="handleImageError">
                <div class="ranking-item-name">{{ item.name }}</div>
                <div class="ranking-item-value">{{ item.value }}{{ ranking.unit }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 活跃时段 & 月度趋势 & 年度大事件 -->
      <div class="section new-section">
        <div class="section-header">
          <div class="section-title">时间脉搏</div>
        </div>
        
        <div class="two-col">
          <!-- 活跃时段 -->
          <div class="new-card">
            <div class="new-card-title">⏰ 活跃时段</div>
            <div class="card-desc">按消息发送小时统计24小时分布</div>
            <div class="hour-chart-container" style="padding:0;box-shadow:none;border:none;">
              <div class="hour-chart">
                <div v-for="(hour, index) in report.statistics?.hourDistribution || {}" :key="index"
                     class="hour-bar" :style="{ height: getHourHeightPercent(hour) + '%' }"></div>
              </div>
              <div class="hour-labels">
                <span>0时</span>
                <span>6时</span>
                <span>12时</span>
                <span>18时</span>
                <span>24时</span>
              </div>
              <div class="hour-peak">
                ⭐ 最活跃时段
                <div class="hour-peak-badge">{{ peakHourText }}</div>
              </div>
            </div>
          </div>
          
          <!-- 月度趋势 -->
          <div v-if="report.statistics?.monthDistribution?.length" class="new-card">
            <div class="new-card-title">📈 月度活跃趋势</div>
            <div class="card-desc">按消息发送时间统计每月消息总数</div>
            <div class="month-chart">
              <div v-for="m in report.statistics.monthDistribution" :key="m.month" class="month-bar-wrap">
                <div class="month-bar-count">{{ m.count }}</div>
                <div class="month-bar" :style="{ height: m.height + '%' }"></div>
                <div class="month-bar-label">{{ m.month.slice(5) }}月</div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 年度大事件（全宽） -->
        <div v-if="report.statistics?.dailyEvents?.length" class="new-card">
          <div class="new-card-title">🔥 年度大事件</div>
          <div class="card-desc">当日消息量超全年均值1.5倍标准差；热词按当日频次÷全年日均的突增度排序</div>
          <div class="event-list">
            <div v-for="e in report.statistics.dailyEvents" :key="e.date" class="event-item">
              <div class="event-date">{{ e.date.slice(5) }}</div>
              <div class="event-count">{{ e.count }}条</div>
              <div class="event-words">
                <span v-for="w in e.top_words" :key="w" class="event-word-tag">{{ w }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 互动关系图谱 -->
      <div v-if="report.statistics?.interactionGraph?.nodes?.length" class="section new-section">
        <div class="section-header">
          <div class="section-title">关系网络</div>
          <img class="section-decor" :src="decorLaugh" alt="装饰">
        </div>
        <div class="new-card">
          <div class="new-card-title">🕸️ 群聊互动图谱</div>
          <div class="card-desc">节点大小=发言量，连线=回复/@互动，仅展示互动≥3次的关系</div>
          <div class="graph-container">
            <canvas ref="graphCanvas"></canvas>
          </div>
          <div class="graph-legend">
            <span><span class="graph-legend-dot" style="background:var(--gold)"></span>节点大小=发言量</span>
            <span><span class="graph-legend-dot" style="background:var(--red)"></span>连线=回复/@互动</span>
          </div>
        </div>
      </div>
      
      <!-- 最佳拍档 & 单向奔赴 -->
      <div v-if="report.statistics?.bestPairs?.length || report.statistics?.oneSided?.length" class="section new-section">
        <div class="section-header">
          <div class="section-title">群聊CP</div>
        </div>
        <div class="two-col">
          <div v-if="report.statistics?.bestPairs?.length" class="new-card">
            <div class="new-card-title">💞 最佳拍档</div>
            <div class="card-desc">两人互相回复/@总次数最高的组合</div>
            <div class="relation-list">
              <div v-for="(p, i) in report.statistics.bestPairs.slice(0,5)" :key="i" class="relation-item">
                <div class="relation-rank">{{ i + 1 }}</div>
                <div class="relation-name">{{ p.a.name }}</div>
                <div class="relation-arrow">⚡</div>
                <div class="relation-name">{{ p.b.name }}</div>
                <div class="relation-value">{{ p.total }}次</div>
              </div>
            </div>
          </div>
          
          <div v-if="report.statistics?.oneSided?.length" class="new-card">
            <div class="new-card-title">💔 单向奔赴</div>
            <div class="card-desc">一方互动≥另一方3倍且主动方≥10次，数值为主动:被动</div>
            <div class="relation-list">
              <div v-for="(o, i) in report.statistics.oneSided.slice(0,5)" :key="i" class="relation-item">
                <div class="relation-rank">{{ i + 1 }}</div>
                <div class="relation-name">{{ o.active.name }}</div>
                <div class="relation-arrow">→</div>
                <div class="relation-name">{{ o.passive.name }}</div>
                <div class="relation-value">{{ o.active_count }}:{{ o.passive_count }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 热场王 & 冷场王 -->
      <div v-if="report.statistics?.heatKing?.length || report.statistics?.coldKing?.length" class="section new-section">
        <div class="section-header">
          <div class="section-title">气氛担当</div>
        </div>
        <div class="two-col">
          <div v-if="report.statistics?.heatKing?.length" class="new-card card-with-decor">
            <img class="card-decor" :src="decorAyakaDrink" alt="热场王装饰">
            <div class="new-card-title">🔥 热场王</div>
            <div class="card-desc">发言后5分钟内群内平均消息数（不含自己），越高越能带节奏</div>
            <div v-for="h in report.statistics.heatKing.slice(0,5)" :key="h.uin" class="heat-bar-item">
              <div class="heat-bar-name">{{ h.name }}</div>
              <div class="heat-bar-track">
                <div class="heat-bar-fill hot" :style="{ width: getHeatPercent(h.avg_after, 'hot') + '%' }"></div>
              </div>
              <div class="heat-bar-val">{{ h.avg_after }}</div>
            </div>
          </div>
          
          <div v-if="report.statistics?.coldKing?.length" class="new-card card-with-decor">
            <img class="card-decor" :src="decorAyakaBai" alt="冷场王装饰">
            <div class="new-card-title">❄️ 冷场王</div>
            <div class="card-desc">发言后5分钟内群内平均消息数最低，发言后群容易冷</div>
            <div v-for="c in report.statistics.coldKing.slice(0,5)" :key="c.uin" class="heat-bar-item">
              <div class="heat-bar-name">{{ c.name }}</div>
              <div class="heat-bar-track">
                <div class="heat-bar-fill cold" :style="{ width: getHeatPercent(c.avg_after, 'cold') + '%' }"></div>
              </div>
              <div class="heat-bar-val">{{ c.avg_after }}</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 口头禅 & 标点狂魔 -->
      <div v-if="report.statistics?.petPhrases?.length || report.statistics?.punctuationData" class="section new-section">
        <div class="section-header">
          <div class="section-title">语言指纹</div>
        </div>
        <div class="two-col">
          <div v-if="report.statistics?.petPhrases?.length" class="new-card card-with-decor">
            <img class="card-decor" :src="decorMaid" alt="口头禅装饰">
            <div class="new-card-title">💬 口头禅</div>
            <div class="card-desc">个人高频词按次数×个人占比排序，已过滤通用词和群友名称</div>
            <div class="pet-grid">
              <div v-for="p in report.statistics.petPhrases.slice(0,15)" :key="p.uin" class="pet-item">
                <img class="pet-avatar" :src="p.avatar" @error="handleImageError">
                <div class="pet-info">
                  <div class="pet-name">{{ p.name }}</div>
                  <div class="pet-words">
                    <span v-for="phrase in p.phrases" :key="phrase.word" class="pet-word">{{ phrase.word }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div v-if="report.statistics?.punctuationData" class="new-card">
            <div class="new-card-title">❗ 标点狂魔</div>
            <div class="card-desc">感叹号/问号/省略号使用总数排行</div>
            <div v-if="report.statistics.punctuationData.exclaim?.length" style="margin-bottom:10px;">
              <div style="font-size:11px;color:var(--gold);margin-bottom:5px;font-weight:700;">感叹号 ❗</div>
              <div v-for="p in report.statistics.punctuationData.exclaim.slice(0,3)" :key="'e'+p.uin" class="punct-row">
                <div class="punct-icon">❗</div>
                <div class="punct-name">{{ p.name }}</div>
                <div class="punct-count">{{ p.value }}</div>
              </div>
            </div>
            <div v-if="report.statistics.punctuationData.question?.length" style="margin-bottom:10px;">
              <div style="font-size:11px;color:var(--gold);margin-bottom:5px;font-weight:700;">问号 ❓</div>
              <div v-for="p in report.statistics.punctuationData.question.slice(0,3)" :key="'q'+p.uin" class="punct-row">
                <div class="punct-icon">❓</div>
                <div class="punct-name">{{ p.name }}</div>
                <div class="punct-count">{{ p.value }}</div>
              </div>
            </div>
            <div v-if="report.statistics.punctuationData.ellipsis?.length">
              <div style="font-size:11px;color:var(--gold);margin-bottom:5px;font-weight:700;">省略号 💭</div>
              <div v-for="p in report.statistics.punctuationData.ellipsis.slice(0,3)" :key="'l'+p.uin" class="punct-row">
                <div class="punct-icon">💭</div>
                <div class="punct-name">{{ p.name }}</div>
                <div class="punct-count">{{ p.value }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 统计说明 -->
      <div class="stats-note-section">
        <div class="section-header">
          <div class="section-title">统计说明</div>
        </div>
        <div class="stats-note-grid">
          <div class="stats-note-item"><strong>月度活跃</strong>按消息发送时间（东八区）统计每月消息总数</div>
          <div class="stats-note-item"><strong>年度大事件</strong>当日消息量超过「均值+1.5倍标准差」或「均值×1.5」（取大值）；热词按「当日出现次数÷全年日均次数」的突增度排序</div>
          <div class="stats-note-item"><strong>关系网络</strong>节点大小=发言量，连线=回复+@互动次数，仅展示互动≥3次的关系对；力导向布局自动聚类</div>
          <div class="stats-note-item"><strong>最佳拍档</strong>两人之间互相回复+@的总互动次数最高的组合</div>
          <div class="stats-note-item"><strong>单向奔赴</strong>一方对另一方的互动次数≥另一方的3倍，且主动方互动≥10次；数值为「主动:被动」</div>
          <div class="stats-note-item"><strong>热场王</strong>每人每条发言后5分钟内、非本人的平均消息数；数值越高说明发言后群越活跃（需≥10条消息才参与排名）</div>
          <div class="stats-note-item"><strong>冷场王</strong>发言后5分钟内群内平均消息数最低的用户；发言后群容易冷场</div>
          <div class="stats-note-item"><strong>口头禅</strong>个人高频词按「使用次数×(个人占比+0.3)」综合排序，已过滤通用助词、代词和所有群友名称</div>
          <div class="stats-note-item"><strong>标点狂魔</strong>感叹号「！!」、问号「？?」、省略号「……」的使用总数排行</div>
          <div class="stats-note-item"><strong>活跃时段</strong>按消息发送小时统计24小时分布，最高峰为消息量最多的小时区间</div>
        </div>
      </div>
      
      <div class="stripe-diagonal"></div>
      
      <!-- 分享按钮区域 -->
      <div class="share-section">
        <div class="share-container">
          <!-- 如果没有生成图片或有错误，显示生成按钮 -->
          <button 
            v-if="!imageUrl || imageError"
            class="share-button" 
            @click="$emit('generate-image')"
            :disabled="generatingImage">
            <span v-if="!generatingImage">
              {{ imageError ? '🔄 重新生成' : '📸 生成图片分享' }}
            </span>
            <span v-else>
              <span class="loading-dots">生成中</span>
            </span>
          </button>
          
          <!-- 如果图片已生成，显示下载和重新生成选项 -->
          <div v-if="imageUrl && !imageError" class="share-result">
            <div class="share-success">✅ 图片已生成并下载</div>
            <div class="share-actions">
              <a :href="imageUrl" :download="imageFileName" class="download-button">
                💾 再次下载
              </a>
              <button class="regenerate-button" @click="$emit('generate-image')">
                🔄 重新生成
              </button>
            </div>
          </div>
          
          <!-- 显示错误信息 -->
          <div v-if="imageError" class="share-error">
            ❌ {{ imageError }}
          </div>
        </div>
      </div>
      
      <!-- 页脚 -->
      <div class="footer">
        <img class="footer-decor" :src="decorChibi" alt="页脚装饰">
        <div class="footer-text">
          Github.com/ZiHuixi/QQgroup-annual-report-analyzer
        </div>
      </div>
      
      <div class="stripe-thin"></div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, nextTick } from 'vue'
import { useReportUtils } from '../composables/useReportUtils'

// 装饰图片
import decorFairy from '../assets/D7A1DE20F9F7A9E55263C6FFD0C3FD17.jpg'
import decorAyakaDrink from '../assets/481845F6DA54FD77BE7AF3320A3CE45B.gif'
import decorAyakaBai from '../assets/270A010E6DD50EC84AB9DF72646620C4.jpg'
import decorMaid from '../assets/04545C1731436C7D0F1AA8EB73C27436.jpg'
import decorLaugh from '../assets/14FD93E402AA5EF74A3B30D19ADD19B1.jpg'
import decorChibi from '../assets/A814FF35DECEF1A81FC1FE0FD3D8AB67.jpg'

// ========== Props ==========
const props = defineProps({
  report: {
    type: Object,
    required: true
  },
  generatingImage: {
    type: Boolean,
    default: false
  },
  imageUrl: {
    type: String,
    default: ''
  },
  imageError: {
    type: String,
    default: ''
  }
})

// ========== Emits ==========
defineEmits(['generate-image'])

// ========== 使用工具函数 ==========
const {
  formatNumber,
  truncateText,
  getTitleClass,
  handleImageError,
  getHourHeight,
  getPeakHour
} = useReportUtils()

// ========== Refs ==========
const graphCanvas = ref(null)

// ========== 计算属性 ==========
// 获取时段高度百分比
const getHourHeightPercent = (hour) => {
  return getHourHeight(hour, props.report.statistics?.hourDistribution)
}

// 获取最活跃时段文本
const peakHourText = computed(() => {
  const peak = getPeakHour(props.report.statistics?.hourDistribution)
  return `${peak}:00 - ${peak + 1}:00`
})

// 获取图片文件名
const imageFileName = computed(() => {
  const chatName = props.report?.chat_name || '报告'
  return `${chatName}_年度报告_${new Date().getTime()}.png`
})

// 热场/冷场百分比
const getHeatPercent = (val, type) => {
  const list = type === 'hot'
    ? props.report.statistics?.heatKing || []
    : props.report.statistics?.coldKing || []
  const max = Math.max(...list.map(h => h.avg_after), 1)
  return Math.round((val / max) * 100)
}

// ========== 力导向图渲染 ==========
const renderGraph = () => {
  const canvas = graphCanvas.value
  if (!canvas) return
  const graph = props.report.statistics?.interactionGraph
  if (!graph || !graph.nodes || !graph.nodes.length) return

  const ctx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1
  const rect = canvas.getBoundingClientRect()
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  ctx.scale(dpr, dpr)
  const W = rect.width, H = rect.height

  let nodes = [...graph.nodes]
  let edges = [...graph.edges]

  // 只保留Top40活跃节点
  nodes.sort((a, b) => b.msgCount - a.msgCount)
  nodes = nodes.slice(0, 40)
  const nodeIds = {}
  nodes.forEach((n, i) => { nodeIds[n.id] = i })
  edges = edges.filter(e => nodeIds[e.source] !== undefined && nodeIds[e.target] !== undefined)

  if (!nodes.length) return

  const maxMsg = Math.max(...nodes.map(n => n.msgCount || 1))
  const maxWeight = Math.max(...edges.map(e => e.weight || 1), 1)

  // 圆形分布初始化
  const cx = W / 2, cy = H / 2
  const R = Math.min(W, H) * 0.42
  nodes.forEach((n, i) => {
    const angle = (i / nodes.length) * Math.PI * 2
    n.x = cx + Math.cos(angle) * R
    n.y = cy + Math.sin(angle) * R
    n.vx = 0; n.vy = 0
  })

  // 力导向模拟
  for (let iter = 0; iter < 300; iter++) {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[j].x - nodes[i].x
        const dy = nodes[j].y - nodes[i].y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = 3500 / (dist * dist)
        const fx = (dx / dist) * force, fy = (dy / dist) * force
        nodes[i].vx -= fx; nodes[i].vy -= fy
        nodes[j].vx += fx; nodes[j].vy += fy
      }
    }
    edges.forEach(e => {
      const si = nodeIds[e.source], ti = nodeIds[e.target]
      if (si === undefined || ti === undefined) return
      const s = nodes[si], t = nodes[ti]
      const dx = t.x - s.x, dy = t.y - s.y
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      const force = (dist - 160) * 0.015 * (e.weight / maxWeight + 0.3)
      const fx = (dx / dist) * force, fy = (dy / dist) * force
      s.vx += fx; s.vy += fy
      t.vx -= fx; t.vy -= fy
    })
    nodes.forEach(n => {
      n.vx += (cx - n.x) * 0.002
      n.vy += (cy - n.y) * 0.002
      n.vx *= 0.9; n.vy *= 0.9
      n.x += n.vx; n.y += n.vy
      n.x = Math.max(20, Math.min(W - 20, n.x))
      n.y = Math.max(20, Math.min(H - 20, n.y))
    })
  }

  // 渲染边
  edges.forEach(e => {
    const si = nodeIds[e.source], ti = nodeIds[e.target]
    if (si === undefined || ti === undefined) return
    const s = nodes[si], t = nodes[ti]
    const alpha = 0.15 + (e.weight / maxWeight) * 0.4
    ctx.strokeStyle = `rgba(91,155,213,${alpha})`
    ctx.lineWidth = 0.8 + (e.weight / maxWeight) * 2.5
    ctx.beginPath()
    ctx.moveTo(s.x, s.y)
    ctx.lineTo(t.x, t.y)
    ctx.stroke()
  })

  // 渲染节点
  nodes.forEach(n => {
    const r = 5 + (n.msgCount / maxMsg) * 18
    const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r * 2.2)
    grad.addColorStop(0, 'rgba(212,168,83,0.35)')
    grad.addColorStop(1, 'rgba(212,168,83,0)')
    ctx.fillStyle = grad
    ctx.beginPath()
    ctx.arc(n.x, n.y, r * 2.2, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = '#d4a853'
    ctx.beginPath()
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2)
    ctx.fill()
    ctx.strokeStyle = '#2c3e6b'
    ctx.lineWidth = 2
    ctx.stroke()
    if (r > 7) {
      ctx.fillStyle = '#2c3e6b'
      ctx.font = 'bold 12px "Noto Sans SC", sans-serif'
      ctx.textAlign = 'center'
      const label = n.name.length > 8 ? n.name.slice(0, 8) + '..' : n.name
      ctx.fillText(label, n.x, n.y + r + 16)
    }
  })
}

onMounted(() => {
  nextTick(() => {
    setTimeout(renderGraph, 100)
  })
})
</script>

<style>
@import '../report-styles.css';
</style>

<style scoped>
.classic-template {
  
}
</style>

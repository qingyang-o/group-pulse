# -*- coding: utf-8 -*-

import os
import sys
import json
import math
import asyncio
from jinja2 import Environment, FileSystemLoader, select_autoescape
import config as cfg
from utils import sanitize_filename
from logger import get_logger

logger = get_logger(__name__)


# 每个词独立的贡献者颜色
WORD_COLORS = [
    '#DC2626', '#EA580C', '#D97706', '#CA8A04', '#65A30D',
    '#16A34A', '#0D9488', '#0891B2', '#2563EB', '#7C3AED'
]

# 榜单配置 (title, key, icon, unit)
RANKING_CONFIG = [
    ('群聊噪音', '话痨榜', '🏆', '条'),
    ('打字民工', '字数榜', '📝', '字'),
    ('小作文狂', '长文王', '📖', ''),
    ('表情狂人', '表情帝', '😂', '个'),
    ('我的图图', '图片狂魔', '🖼️', '张'),
    ('转发机器', '合并转发王', '📦', '次'),
    ('回复劳模', '回复狂', '💬', '次'),
    ('回复黑洞', '被回复最多', '⭐', '次'),
    ('艾特狂魔', '艾特狂', '📢', '次'),
    ('人气靶子', '被艾特最多', '🎯', '次'),
    ('链接仓鼠', '链接分享王', '🔗', '条'),
    ('阴间作息', '深夜党', '🌙', '条'),
    ('早八怨种', '早起鸟', '🌅', '条'),
    ('复读机器', '复读机', '🔄', '次'),
]


def format_number(value):
    """格式化数字"""
    try:
        return f"{int(value):,}"
    except:
        return str(value)


def truncate_text(text, length=50):
    """截断文本"""
    if not text:
        return ""
    text = text.replace('\n', ' ').strip()
    if len(text) > length:
        return text[:length] + '...'
    return text


def get_avatar_url(uin):
    """获取QQ头像URL"""
    return f"https://q1.qlogo.cn/g?b=qq&nk={uin}&s=640"


def clean_ai_response(text):
    # 清理AI响应中的思考过程标记
    if not text:
        return text
    
    import re
    
    # 移除常见的思考标记模式
    patterns = [
        r'\*Thinking[:\.].*?\*.*?(?=\n\n|\Z)', 
        r'\*\*Examining.*?\*\*.*?(?=\n\n|\Z)',  
        r'<thinking>.*?</thinking>',  
        r'【思考】.*?【/思考】',  
        r'\[思考过程\].*?(?=\n\n|\Z)',  
    ]
    
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    # 如果整段都是thinking内容，尝试提取最后一行作为结论
    if cleaned.strip() == '' or len(cleaned.strip()) < 5:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        # 尝试找到不是thinking标记的最后几行
        for line in reversed(lines):
            if not any(marker in line.lower() for marker in ['thinking', 'examining', '思考', 'analysis']):
                if len(line) > 5 and len(line) < 100:  # 合理长度
                    return line
    
    return cleaned.strip()


class AIWordSelector:
    """AI智能选词器"""
    
    SYSTEM_PROMPT = """你是一个专业的群聊文化分析师，擅长识别最具代表性的群聊热词。

你的任务是从候选词列表中选出10个最适合作为年度热词的词汇。选词标准：
1. **使用量大**：高频出现的词更能代表群聊文化
2. **新颖有趣**：独特、有创意、有梗的词优先
3. **搞笑幽默**：能引发笑点的词、梗词、谐音梗等
4. **群聊特色**：体现这个群独特氛围和风格的词
5. **不避讳粗俗**：脏话、粗话、网络黑话如果有特色也可以选

优先考虑：
- 网络流行梗、热词
- 群内特有的黑话、缩写
- 搞笑表情、emoji组合
- 有趣的口头禅
- 独特的表达方式

请从提供的候选词中选出最能代表这个群聊文化的10个词。"""

    def __init__(self):
        self.client = None
        self.model = None
        self._init_client()
    
    def _init_client(self):
        """初始化OpenAI客户端"""
        # 支持从环境变量读取API密钥
        api_key = os.getenv('OPENAI_API_KEY', cfg.OPENAI_API_KEY)
        base_url = os.getenv('OPENAI_BASE_URL', cfg.OPENAI_BASE_URL)
        self.model = os.getenv('OPENAI_MODEL', cfg.OPENAI_MODEL)
        
        if not api_key or api_key == "sk-your-api-key-here":
            logger.warning("⚠️ 未配置OpenAI API Key，无法使用AI选词")
            return
        
        if not self.model:
            logger.warning("⚠️ 未配置OpenAI模型")
            return
        
        try:
            from openai import OpenAI
            import httpx
            
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=httpx.Client(timeout=120.0)
            )
            logger.info(f"✅ AI客户端初始化成功 (模型: {self.model})")
        except Exception as e:
            logger.warning(f"⚠️ OpenAI客户端初始化失败: {e}")
    
    def select_words(self, candidate_words, top_n=200):
        """从候选词中智能选出10个年度热词"""
        if not self.client:
            logger.error("❌ AI未启用，请配置OpenAI API Key")
            return None
        
        # 准备候选词列表（取前top_n个）
        candidates = candidate_words[:top_n]
        
        # 构建候选词信息
        words_info = []
        for idx, word_data in enumerate(candidates, 1):
            word = word_data['word']
            freq = word_data['freq']
            samples = word_data.get('samples', [])
            sample_preview = samples[0][:30] if samples else '无样本'
            
            words_info.append(f"{idx}. {word} ({freq}次) - 样本: {sample_preview}")
        
        words_text = '\n'.join(words_info)
        
        user_prompt = f"""请从以下{len(candidates)}个候选词中选出10个最适合作为年度热词的词汇：

{words_text}

要求：
1. 选出的词要有代表性、有趣味、有群聊特色
2. 优先选择使用量大且有特色的词
3. 不要回避脏话粗话，只要有特色就可以
4. 直接输出10个序号，用逗号分隔，例如: 1,5,8,12,15,23,30,42,56,78
5. 只输出序号，不要有其他文字
6. 尽量选择前100的，除非后面有特别有趣的词
7. 尽量不要选择“啊”等无意义填充词，除非在例句中使用的特别有趣"""

        try:
            logger.info("🤖 AI正在分析并选择年度热词...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            # 清理响应中的思考过程
            raw_result = response.choices[0].message.content.strip()
            result = clean_ai_response(raw_result)
            
            # 如果清理后为空，使用原始结果
            if not result:
                result = raw_result
            
            logger.debug(f"   AI返回: {result}")
            
            # 解析序号
            indices = []
            for part in result.replace('，', ',').split(','):
                try:
                    idx = int(part.strip())
                    if 1 <= idx <= len(candidates):
                        indices.append(idx - 1)  # 转为0索引
                except:
                    continue
            
            if len(indices) < 10:
                logger.warning(f"⚠️ AI只选出{len(indices)}个词，自动补充前几个...")
                # 补充前面的词直到10个
                for i in range(len(candidates)):
                    if i not in indices and len(indices) < 10:
                        indices.append(i)
            
            indices = indices[:10]
            selected = [candidates[i] for i in indices]
            
            logger.info("\n✅ AI选词完成:")
            for i, word_data in enumerate(selected, 1):
                logger.info(f"   {i}. {word_data['word']} ({word_data['freq']}次)")
            
            return selected
            
        except Exception as e:
            logger.error(f"❌ AI选词失败: {e}")
            return None


class AICommentGenerator:
    """AI锐评生成器"""
    
    SYSTEM_PROMPT = """你是一个幽默风趣的群聊分析师，擅长用犀利又不失温度的语言点评网络热词。

你的任务是为QQ群年度热词报告生成一句精辟的锐评。要求：
1. 简短有力，15-30字为宜
2. 可以调侃、可以感慨、可以哲理，但要有趣
3. 结合词语本身的含义和使用场景
4. 语气可以是：毒舌吐槽/温情感慨/哲学思考/冷幽默/谐音梗 等
5. 不要太正经，要有网感

风格参考：
- "哈哈哈" → "快乐是假的，但敷衍是真的"
- "牛逼" → "词汇量告急时的唯一出路"
- "好的" → "成年人最敷衍的三个字"
- "?" → "一个符号，十万种质疑"
- "6" → "当代网友最高效的赞美"""

    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化OpenAI客户端"""
        # 支持从环境变量读取API密钥
        api_key = os.getenv('OPENAI_API_KEY', cfg.OPENAI_API_KEY)
        base_url = os.getenv('OPENAI_BASE_URL', cfg.OPENAI_BASE_URL)
        model = os.getenv('OPENAI_MODEL', cfg.OPENAI_MODEL)
        
        if not api_key or api_key == "sk-your-api-key-here":
            logger.warning("⚠️ 未配置OpenAI API Key，将跳过AI锐评")
            return
        
        try:
            from openai import OpenAI
            import httpx
            
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=httpx.Client(timeout=60.0)  # 增加超时
            )
            
            # 调试信息
            if os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'):
                logger.debug("🌐 系统代理已自动加载")
                
        except Exception as e:
            logger.warning(f"⚠️ OpenAI客户端初始化失败: {e}")
    
    def generate_comment(self, word, freq, samples):
        """为单个词生成锐评"""
        if not self.client:
            return self._fallback_comment(word)
        
        # 构建用户提示
        samples_text = '\n'.join(f'- {s[:50]}' for s in samples[:5]) if samples else '无'
        
        user_prompt = f"""请为这个群聊热词生成一句锐评：

词语：{word}
出现次数：{freq}次
使用样本：
{samples_text}

直接输出锐评内容，不要加引号或其他格式。"""

        try:
            # 尝试调用API，如果失败则降级处理
            response = self.client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', cfg.OPENAI_MODEL),
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            # 清理响应中的思考过程
            raw_content = response.choices[0].message.content.strip()
            cleaned_content = clean_ai_response(raw_content)
            
            # 如果清理后为空或太短，使用备用
            if not cleaned_content or len(cleaned_content) < 5:
                return self._fallback_comment(word)
            
            return cleaned_content
        except Exception as e:
            logger.warning(f"   ⚠️ AI生成失败({word}): {e}")
            return self._fallback_comment(word)
    
    def _fallback_comment(self, word):
        """备用锐评"""
        import config as cfg
        import random
        fallbacks = getattr(cfg, "FALLBACK_COMMENTS", [
            "群友的快乐，简单又纯粹",
            "这个词承载了太多故事",
            "高频出现，必有原因",
            "群聊精华，浓缩于此",
            "每一次使用都是一次认同",
        ])
        return random.choice(fallbacks)
    
    def generate_batch(self, words_data):
        """批量生成锐评"""
        if not self.client:
            logger.warning("⚠️ AI未启用，使用默认锐评")
            return {w['word']: self._fallback_comment(w['word']) for w in words_data}
        
        logger.info("🤖 正在生成AI锐评...")
        comments = {}
        for i, word_info in enumerate(words_data, 1):
            word = word_info['word']
            logger.info(f"   [{i}/{len(words_data)}] {word}...")
            comment = self.generate_comment(
                word, 
                word_info['freq'], 
                word_info.get('samples', [])
            )
            comments[word] = comment
            logger.info(f"✓")
        
        return comments


class ImageGenerator:
    """图片报告生成器"""
    
    def __init__(self, analyzer=None, json_path=None, output_dir=None):
        self.analyzer = analyzer
        self.json_data = None
        self.selected_words = []
        self.ai_comments = {}
        self.output_dir = output_dir or os.path.dirname(os.path.abspath(cfg.INPUT_FILE))
        self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        
        if json_path and os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
        elif analyzer:
            self.json_data = analyzer.export_json()
        
        self.enabled = cfg.ENABLE_IMAGE_EXPORT
        self.ai_selector = None
    
    def display_words_for_selection(self):
        """展示词汇供用户选择"""
        if not self.json_data:
            logger.error("❌ 无数据可展示")
            return False
        
        top_words = self.json_data.get('topWords', [])
        if not top_words:
            logger.error("❌ 无热词数据")
            return False
        
        logger.info("\n" + "=" * 70)
        logger.info("📝 请从以下热词中选择 10 个作为年度热词")
        logger.info("=" * 70)
        
        page_size = 50
        total_pages = (len(top_words) + page_size - 1) // page_size
        current_page = 0
        
        while True:
            start = current_page * page_size
            end = min(start + page_size, len(top_words))
            
            logger.info(f"\n📄 第 {current_page + 1}/{total_pages} 页 ({start + 1}-{end})")
            logger.info("-" * 70)
            
            for i in range(start, end):
                word_info = top_words[i]
                word = word_info['word']
                freq = word_info['freq']
                samples = word_info.get('samples', [])
                
                sample_preview = samples[0].replace('\n', ' ')[:25] + '...' if samples and len(samples[0]) > 25 else (samples[0].replace('\n', ' ') if samples else '无样本')
                contributors = word_info.get('contributors', [])
                contrib_str = contributors[0]['name'] if contributors else '未知'
                
                logger.info(f"  {i+1:>3}. {word:<8} ({freq:>4}次) 👤{contrib_str:<10} | {sample_preview}")
            
            logger.info("-" * 70)
            logger.info("📌 [n]下一页 [p]上一页 [v 序号]详情 [s]选择 [q]退出")
            
            cmd = input(">>> ").strip().lower()
            
            if cmd == 'n':
                current_page = min(current_page + 1, total_pages - 1)
            elif cmd == 'p':
                current_page = max(current_page - 1, 0)
            elif cmd == 's':
                return self._get_user_selection(top_words)
            elif cmd.startswith('v'):
                try:
                    idx = int(cmd[1:].strip()) - 1
                    if 0 <= idx < len(top_words):
                        self._show_word_detail(top_words[idx], idx + 1)
                except:
                    logger.warning("⚠️ 请输入有效序号")
            elif cmd == 'q':
                return False
        
        return False
    
    def _show_word_detail(self, word_info, idx):
        """显示词汇详情"""
        logger.info(f"\n{'='*60}")
        logger.info(f"【{idx}】{word_info['word']} - {word_info['freq']}次")
        logger.info(f"{'='*60}")
        
        contributors = word_info.get('contributors', [])
        if contributors:
            logger.info("\n👤 贡献者:")
            max_count = contributors[0]['count']
            for i, c in enumerate(contributors[:5], 1):
                bar = '█' * int(c['count'] / max_count * 20)
                logger.info(f"   {i}. {c['name']:<12} {bar} {c['count']}次")
        
        samples = word_info.get('samples', [])
        if samples:
            logger.info(f"\n📋 样本:")
            for i, s in enumerate(samples[:5], 1):
                logger.info(f"   {i}. {s.replace(chr(10), ' ')[:60]}")
        
        input("\n按回车继续...")
    
    def _get_user_selection(self, top_words):
        """获取用户选择"""
        logger.info("\n" + "=" * 60)
        logger.info("📝 输入10个序号 (空格/逗号分隔，支持范围如1-5)")
        
        while True:
            selection = input("\n>>> ").strip()
            if not selection:
                continue
            
            indices = []
            for part in selection.replace(',', ' ').replace('，', ' ').split():
                try:
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        indices.extend(range(start - 1, end))
                    else:
                        indices.append(int(part) - 1)
                except:
                    pass
            
            indices = [i for i in indices if 0 <= i < len(top_words)]
            indices = list(dict.fromkeys(indices))  # 去重保序
            
            if len(indices) < 10:
                logger.warning(f"⚠️ 需要10个，当前{len(indices)}个: {[i+1 for i in indices]}")
                continue
            
            indices = indices[:10]
            self.selected_words = [top_words[i] for i in indices]
            
            logger.info("\n✅ 已选:")
            for i, w in enumerate(self.selected_words, 1):
                logger.info(f"   {i}. {w['word']} ({w['freq']}次)")
            
            if input("\n确认? [Y/n]: ").strip().lower() in ('', 'y', 'yes'):
                return True
    
    def _prepare_template_data(self):
        """准备模板数据"""
        max_freq = max(w['freq'] for w in self.selected_words)
        min_freq = min(w['freq'] for w in self.selected_words)
        
        def calc_bar_height(freq):
            if max_freq == min_freq:
                return 80
            normalized = (freq - min_freq) / (max_freq - min_freq)
            return 25 + math.sqrt(normalized) * 75
        
        processed_words = []
        for idx, word_info in enumerate(self.selected_words):
            contributors = word_info.get('contributors', [])
            total = word_info['freq']
            
            # 每个词独立分配颜色给其贡献者
            segments = []
            accounted = 0
            word_contributor_colors = {}
            
            for i, c in enumerate(contributors[:5]):
                color = WORD_COLORS[i % len(WORD_COLORS)]
                word_contributor_colors[c['name']] = color
                percent = (c['count'] / total * 100) if total > 0 else 0
                segments.append({
                    'name': c['name'],
                    'uin': c.get('uin', ''),
                    'count': c['count'],
                    'percent': percent,
                    'color': color
                })
                accounted += c['count']
            
            # 其他
            if accounted < total:
                other = total - accounted
                segments.append({
                    'name': '其他',
                    'uin': '',
                    'count': other,
                    'percent': (other / total * 100),
                    'color': '#6B7280'
                })
            
            # 图例（该词的贡献者）
            legend = []
            for c in contributors[:3]:
                legend.append({
                    'name': c['name'], 
                    'color': word_contributor_colors.get(c['name'], '#6B7280')
                })
            while len(legend) < 3:
                legend.append({'name': '', 'color': 'transparent'})            
            # 主要贡献者文本
            contrib_text = '、'.join(c['name'] for c in contributors[:3]) if contributors else '未知'
            
            # AI锐评
            ai_comment = self.ai_comments.get(word_info['word'], '')
            
            processed_words.append({
                'word': word_info['word'],
                'freq': word_info['freq'],
                'bar_height': calc_bar_height(word_info['freq']),
                'segments': segments,
                'legend': legend,
                'samples': word_info.get('samples', []),
                'contributors_text': contrib_text,
                'top_contributor': contributors[0] if contributors else None,
                'ai_comment': ai_comment,
                'color': WORD_COLORS[idx % len(WORD_COLORS)]
            })
        
        # 榜单数据
        rankings_data = self.json_data.get('rankings', {})
        processed_rankings = []
        
        for title, key, icon, unit in RANKING_CONFIG:
            data = rankings_data.get(key, [])
            if not data:
                continue
            
            first = data[0] if data else None
            others = data[1:5] if len(data) > 1 else []
            
            processed_rankings.append({
                'title': title,
                'icon': icon,
                'unit': unit,
                'first': {
                    'name': first.get('name', '未知'),
                    'uin': first.get('uin', ''),
                    'value': first.get('value', 0),
                    'avatar': get_avatar_url(first.get('uin', '')) if first else ''
                } if first else None,
                'others': [
                    {
                        'name': item.get('name', '未知'),
                        'value': item.get('value', 0),
                        'uin': item.get('uin', ''),
                        'avatar': get_avatar_url(item.get('uin', ''))
                    }
                    for item in others
                ]
            })
        
        # 24小时分布
        hour_dist = self.json_data.get('hourDistribution', {})
        max_hour = max((int(hour_dist.get(str(h), 0)) for h in range(24)), default=1)
        peak_hour = max(range(24), key=lambda h: int(hour_dist.get(str(h), 0)))
        
        hour_data = []
        for h in range(24):
            count = int(hour_dist.get(str(h), 0))
            height = max((count / max_hour * 100) if max_hour > 0 else 0, 3)
            hour_data.append({'hour': h, 'count': count, 'height': height})
        
        # ===== 新增维度数据处理 =====
        
        # 月度活跃分布
        month_dist = self.json_data.get('monthDistribution', {})
        month_data = []
        if month_dist:
            max_month = max(month_dist.values())
            for month in sorted(month_dist.keys()):
                count = month_dist[month]
                height = max((count / max_month * 100) if max_month > 0 else 0, 3)
                month_data.append({'month': month, 'count': count, 'height': height})
        
        # 年度大事件
        daily_events = self.json_data.get('dailyEvents', [])
        
        # 热场王/冷场王
        heat_king = self.json_data.get('heatKing', [])
        cold_king = self.json_data.get('coldKing', [])
        
        # 最佳拍档
        best_pairs = self.json_data.get('bestPairs', [])
        
        # 单向奔赴
        one_sided = self.json_data.get('oneSided', [])
        
        # 口头禅（取发言量Top10用户）
        pet_phrases_raw = self.json_data.get('petPhrases', {})
        rankings_data_all = self.json_data.get('rankings', {})
        talkers = rankings_data_all.get('话痨榜', [])[:10]
        pet_phrases = []
        for talker in talkers:
            uin = talker.get('uin', '')
            phrases = pet_phrases_raw.get(uin, [])
            if phrases:
                pet_phrases.append({
                    'name': talker.get('name', '未知'),
                    'uin': uin,
                    'avatar': get_avatar_url(uin),
                    'phrases': phrases[:3]
                })
        
        # 标点狂魔
        punct = self.json_data.get('punctuationRankings', {})
        punctuation_data = {
            'exclaim': punct.get('exclaim', [])[:5],
            'question': punct.get('question', [])[:5],
            'ellipsis': punct.get('ellipsis', [])[:5],
        }
        
        # 互动关系图谱（直接传递，前端JS渲染）
        interaction_graph = self.json_data.get('interactionGraph', {})
        
        return {
            'chat_name': self.json_data.get('chatName', '未知群聊'),
            'message_count': self.json_data.get('messageCount', 0),
            'selected_words': processed_words,
            'rankings': processed_rankings,
            'hour_data': hour_data,
            'peak_hour': peak_hour,
            'month_data': month_data,
            'daily_events': daily_events,
            'heat_king': heat_king,
            'cold_king': cold_king,
            'best_pairs': best_pairs,
            'one_sided': one_sided,
            'pet_phrases': pet_phrases,
            'punctuation_data': punctuation_data,
            'interaction_graph': interaction_graph,
        }
    
    def _generate_ai_comments(self, enable_ai=False):
        """生成AI锐评（可静默）"""
        ai_gen = AICommentGenerator()
        if enable_ai and ai_gen.client:
            self.ai_comments = ai_gen.generate_batch(self.selected_words)
        else:
            self.ai_comments = {w['word']: ai_gen._fallback_comment(w['word']) 
                              for w in self.selected_words}
    
    def generate_html(self):
        """生成HTML"""
        if not self.selected_words:
            logger.error("❌ 未选择热词")
            return None
        
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir)
        
        template_path = os.path.join(self.template_dir, 'report_template.html')
        if not os.path.exists(template_path):
            logger.error(f"❌ 模板不存在: {template_path}")
            return None
        
        env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html'])
        )
        env.filters['format_number'] = format_number
        env.filters['truncate_text'] = truncate_text
        env.filters['avatar_url'] = get_avatar_url
        
        template = env.get_template('report_template.html')
        data = self._prepare_template_data()
        html_content = template.render(**data)
        
        safe_name = sanitize_filename(self.json_data.get('chatName', '未知'))
        html_path = os.path.join(self.output_dir, f"{safe_name}_年度热词报告.html")
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"✅ HTML: {html_path}")
        return html_path
    
    async def _html_to_image_async(self, html_path, output_path):
        """异步转图片 - 高分辨率"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("❌ 需要: pip install playwright && playwright install chromium")
            return None
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            # 使用 device_scale_factor=3 提高分辨率（3倍）
            page = await browser.new_page(
                viewport={'width': 1080, 'height': 800},
                device_scale_factor=2  # 高清截图
            )
            await page.goto(f'file://{os.path.abspath(html_path)}')
            await page.wait_for_timeout(2000)
            height = await page.evaluate('document.body.scrollHeight')
            await page.set_viewport_size({'width': 1080, 'height': height + 50})
            await page.wait_for_timeout(500)
            await page.screenshot(path=output_path, full_page=True)
            await browser.close()
        
        return output_path

    
    def html_to_image(self, html_path):
        """转图片"""
        safe_name = sanitize_filename(self.json_data.get('chatName', '未知'))
        output_path = os.path.join(self.output_dir, f"{safe_name}_年度热词报告.png")
        
        logger.info("🖼️ 转换为图片...")
        try:
            result = asyncio.run(self._html_to_image_async(html_path, output_path))
            if result:
                logger.info(f"✅ 图片: {output_path}")
                return output_path
        except Exception as e:
            logger.warning(f"⚠️ 转换失败: {e}")
        
        return None
    
    def generate(self, auto_select=False, ai_select=False, non_interactive=False, generate_image=False, enable_ai=False):
        """生成报告
        
        参数:
            auto_select: 自动选择前10个（简单模式）
            ai_select: 使用AI智能选词（从前200个中选出最有趣的10个）
            non_interactive: 非交互模式
            generate_image: 是否生成图片
            enable_ai: 是否启用AI锐评
        """
        if not self.json_data:
            logger.error("❌ 无数据")
            return None, None
        
        # AI 智能选词模式
        if ai_select:
            logger.info("\n" + "=" * 60)
            logger.info("🤖 AI智能选词模式")
            logger.info("=" * 60)
            
            top_words = self.json_data.get('topWords', [])
            if not top_words:
                logger.error("❌ 无热词数据")
                return None, None
            
            # 初始化AI选词器
            if not self.ai_selector:
                self.ai_selector = AIWordSelector()
            
            # AI选词
            self.selected_words = self.ai_selector.select_words(top_words, top_n=200)
            
            if not self.selected_words:
                logger.warning("⚠️ AI选词失败，改用自动选择前10个")
                self.selected_words = top_words[:10]
        
        # 简单自动选择模式
        elif auto_select or non_interactive:
            self.selected_words = self.json_data.get('topWords', [])[:10]
            logger.info(f"📝 自动选择前10个热词")
        
        # 交互选择模式
        else:
            if not self.display_words_for_selection():
                return None, None
        
        if not self.selected_words:
            return None, None
        
        # AI锐评
        self._generate_ai_comments(enable_ai)
        
        logger.info("\n🎨 生成报告...")
        html_path = self.generate_html()
        if not html_path:
            return None, None
        
        img_path = None
        if generate_image:
            img_path = self.html_to_image(html_path)
        
        return html_path, img_path


def interactive_generate(json_path=None, analyzer=None):
    """交互式选词生成"""
    gen = ImageGenerator(analyzer=analyzer, json_path=json_path)
    gen.enabled = True
    return gen.generate(auto_select=False, enable_ai=True, generate_image=True)


def auto_generate(json_path=None, analyzer=None):
    """自动选择前10个生成"""
    gen = ImageGenerator(analyzer=analyzer, json_path=json_path)
    gen.enabled = True
    return gen.generate(auto_select=True, enable_ai=True, generate_image=True)


def ai_generate(json_path=None, analyzer=None):
    """AI智能选词生成"""
    gen = ImageGenerator(analyzer=analyzer, json_path=json_path)
    gen.enabled = True
    return gen.generate(ai_select=True, enable_ai=True, generate_image=True)


if __name__ == '__main__':
    import glob
    
    logger.info("=" * 60)
    logger.info("🖼️  报告生成器 ")
    logger.info("=" * 60)
    
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    else:
        json_files = glob.glob('*_分析结果.json')
        if not json_files:
            logger.error("❌ 未找到JSON文件")
            sys.exit(1)
        if len(json_files) == 1:
            json_path = json_files[0]
        else:
            for i, f in enumerate(json_files, 1):
                logger.info(f"  {i}. {f}")
            json_path = json_files[int(input("选择: ")) - 1]
    
    logger.info(f"\n📂 {json_path}")
    
    logger.info("\n选择模式:")
    logger.info("  1. 交互选词 - 手动选择10个热词")
    logger.info("  2. 自动前10 - 直接选择前10个")
    logger.info("  3. AI智能选词 - 让AI从前200个中挑选最有趣的10个 🤖")
    
    mode = input("\n请选择 [1/2/3]: ").strip()
    
    if mode == '3':
        html_path, img_path = ai_generate(json_path=json_path)
    elif mode == '2':
        html_path, img_path = auto_generate(json_path=json_path)
    else:
        html_path, img_path = interactive_generate(json_path=json_path)
    
    logger.info("\n" + "=" * 60)
    if html_path:
        logger.info(f"📄 {html_path}")
    if img_path:
        logger.info(f"🖼️ {img_path}")

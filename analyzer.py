# -*- coding: utf-8 -*-
import re
import random
import string
import math
import jieba
from collections import Counter, defaultdict
import config as cfg
from utils import (
    extract_emojis,
    is_emoji,
    parse_timestamp,
    parse_datetime,
    clean_text,
    calculate_entropy,
    analyze_single_chars,
)
from logger import get_logger, init_logging

init_logging()

jieba.setLogLevel(jieba.logging.INFO)

logger = get_logger('analyzer')

# 扩充的中文停用词表（助词、代词、连词、副词、疑问词、通用动词等）
CHINESE_STOPWORDS = {
    '的', '了', '是', '在', '有', '和', '就', '不', '也', '都', '要', '会', '能', '可以', '没有', '不是',
    '这', '那', '这个', '那个', '这些', '那些', '这样', '那样', '怎么', '什么', '为什么', '哪', '哪里',
    '我', '你', '他', '她', '它', '我们', '你们', '他们', '自己', '人家', '别人', '大家', '咱', '咱们',
    '一', '一个', '一下', '一些', '一样', '一直', '已经', '还是', '还有', '一旦', '一共', '一起',
    '但', '但是', '而', '而且', '所以', '因为', '如果', '虽然', '不过', '然后', '接着', '于是', '因此',
    '很', '非常', '特别', '比较', '更', '最', '太', '真的', '确实', '其实', '感觉', '觉得', '反正',
    '现在', '刚才', '正在', '马上', '立刻', '突然', '终于', '最后', '之前', '以后', '后来', '当时',
    '说', '看', '想', '知道', '认为', '以为', '告诉', '问', '回答', '听说', '看来', '看样子',
    '来', '去', '到', '上', '下', '出', '进', '过', '回', '起', '过来', '过去',
    '把', '被', '让', '给', '对', '从', '向', '往', '由', '以', '用', '靠',
    '啊', '吧', '呢', '吗', '哦', '哈', '呀', '嘛', '哇', '唉', '嗯', '呃', '诶', '噢',
    '的话', '而已', '罢了', '似的', '一般', '之类', '等等', '什么的',
    '可能', '应该', '必须', '需要', '想要', '打算', '准备', '好像', '似乎', '大概',
    '时候', '地方', '东西', '事情', '问题', '情况', '样子', '结果', '方面', '程度',
    '就是', '只是', '只有', '只能', '只要', '不管', '无论', '除非', '假如', '要是',
    '那么', '这么', '那么样', '这么样', '怎样', '怎么样',
    '哈哈', '呵呵', '嘻嘻', '嘿嘿', '嗯嗯', '啊啊',
    '个', '只', '条', '件', '张', '块', '本', '篇', '首', '台', '辆',
    '做', '干', '搞', '弄', '整', '办', '处理', '进行',
    '好', '行', '对', '没错', '当然', '肯定', '一定', '绝对',
    '没', '无', '非', '未', '莫', '勿',
    '其', '之', '乎', '者', '也', '矣', '焉', '哉',
    '把它', '这个是', '那个是', '这是', '那是',
    '真', '假', '新', '旧', '老', '大', '小', '多', '少', '高', '低', '长', '短',
    '前', '后', '左', '右', '里', '外', '中', '内', '旁',
    '今天', '明天', '昨天', '前天', '后天', '今年', '去年', '明年',
    '点', '分', '秒', '小时', '分钟', '天', '周', '月', '年',
    '次', '遍', '趟', '回', '顿', '场',
}

class ChatAnalyzer:
    def __init__(self, data):
        self.data = data
        self.messages = data.get('messages', [])
        self.chat_name = data.get('chatName', data.get('chatInfo', {}).get('name', '未知群聊'))
        
        # 应用时间范围过滤
        self._filter_messages_by_time()
        self.uin_to_name = {}
        self.uin_all_names = {}  # 每个 uin 的所有历史昵称（用于口头禅过滤）
        self.recall_names = set()  # 撤回消息中出现的昵称（用于口头禅过滤）
        self.msgid_to_sender = {}
        self.word_freq = Counter()
        self.word_samples = defaultdict(list)
        self.word_contributors = defaultdict(Counter)
        self.user_msg_count = Counter()
        self.user_char_count = Counter()
        self.user_char_per_msg = {}
        self.user_image_count = Counter()
        self.user_forward_count = Counter()
        self.user_reply_count = Counter()
        self.user_replied_count = Counter()
        self.user_at_count = Counter()
        self.user_ated_count = Counter()
        self.user_emoji_count = Counter()
        self.user_link_count = Counter()
        self.user_night_count = Counter()
        self.user_morning_count = Counter()
        self.user_repeat_count = Counter()
        self.hour_distribution = Counter()
        self.month_distribution = Counter()       # 月度消息量
        self.daily_distribution = Counter()       # 每日消息量 "YYYY-MM-DD" -> count
        self.daily_word_freq = defaultdict(Counter)  # 每日热词
        # 互动关系图：interaction_graph[sender_uin][target_uin] = 互动次数
        self.interaction_graph = defaultdict(Counter)
        self.uid_to_uin = {}                      # uid -> uin 映射
        # 个人词频（用于口头禅）
        self.user_word_freq = defaultdict(Counter)
        # 标点统计
        self.user_punctuation = defaultdict(lambda: {'exclaim': 0, 'question': 0, 'ellipsis': 0, 'total_chars': 0})
        # 热场/冷场：每人每条消息后5分钟内的他人消息量
        self.user_heat_scores = defaultdict(list)
        self.discovered_words = set()
        self.merged_words = {}
        self.single_char_stats = {}  # 单字统计
        self.cleaned_texts = []  # 缓存清洗后的文本
        self._build_mappings()
    
    def _filter_messages_by_time(self):
        """根据配置的时间范围过滤消息"""
        if cfg.MESSAGE_START_DATE is None and cfg.MESSAGE_END_DATE is None:
            return  # 无时间限制，不过滤
        
        from datetime import datetime
        
        # 解析配置的日期
        start_dt = None
        end_dt = None
        
        if cfg.MESSAGE_START_DATE:
            try:
                start_dt = datetime.strptime(cfg.MESSAGE_START_DATE, '%Y-%m-%d')
                start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                # 转换为东八区
                from datetime import timezone, timedelta
                start_dt = start_dt.replace(tzinfo=timezone(timedelta(hours=8)))
            except Exception as e:
                logger.warning(f"起始日期格式错误: {cfg.MESSAGE_START_DATE}, 错误: {e}")
        
        if cfg.MESSAGE_END_DATE:
            try:
                end_dt = datetime.strptime(cfg.MESSAGE_END_DATE, '%Y-%m-%d')
                end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                # 转换为东八区
                from datetime import timezone, timedelta
                end_dt = end_dt.replace(tzinfo=timezone(timedelta(hours=8)))
            except Exception as e:
                logger.warning(f"结束日期格式错误: {cfg.MESSAGE_END_DATE}, 错误: {e}")
        
        if start_dt is None and end_dt is None:
            return  # 日期解析失败，不过滤
        
        # 过滤消息
        original_count = len(self.messages)
        filtered_messages = []
        
        for msg in self.messages:
            timestamp = msg.get('timestamp', '')
            msg_dt = parse_datetime(timestamp)
            
            if msg_dt is None:
                continue 
            
            # 检查是否在时间范围内
            if start_dt and msg_dt < start_dt:
                continue
            if end_dt and msg_dt > end_dt:
                continue
            
            filtered_messages.append(msg)
        
        self.messages = filtered_messages
        filtered_count = len(self.messages)
        
        if start_dt or end_dt:
            time_range = []
            if start_dt:
                time_range.append(f"从 {cfg.MESSAGE_START_DATE}")
            if end_dt:
                time_range.append(f"到 {cfg.MESSAGE_END_DATE}")
            logger.info(f"⏰ 时间范围过滤: {' '.join(time_range)}")
            logger.info(f"   原始消息: {original_count} 条, 过滤后: {filtered_count} 条")

    def _is_bot_message(self, msg):
        """判断是否为机器人消息（基于 subMsgType）"""
        if not cfg.FILTER_BOT_MESSAGES:
            return False
        
        raw_msg = msg.get('rawMessage', {})
        sub_msg_type = raw_msg.get('subMsgType', 0)
        return sub_msg_type in [577, 65]

    def _build_mappings(self):
        # 构建 uin 到 name 的映射，优先保留有效的 name
        # 先收集每个 uin 的所有 name（按顺序）和 sendMemberName
        uin_names = defaultdict(list)
        uin_member_names = {}  # 存储最后的 sendMemberName
        
        for msg in self.messages:
            if self._is_bot_message(msg):
                continue
            
            sender = msg.get('sender', {})
            uin = sender.get('uin')
            uid = sender.get('uid')
            name = sender.get('name', '').strip()
            msg_id = msg.get('messageId')
            
            if uin and uid:
                self.uid_to_uin[uid] = uin
            
            if uin and name:
                # 只在 name 与上一个不同时添加
                if not uin_names[uin] or uin_names[uin][-1] != name:
                    uin_names[uin].append(name)
            
            # 收集 sendMemberName（保留最后一个）
            if uin:
                raw_msg = msg.get('rawMessage', {})
                send_member_name = raw_msg.get('sendMemberName', '').strip()
                if send_member_name:
                    uin_member_names[uin] = send_member_name
            
            if msg_id and uin:
                self.msgid_to_sender[msg_id] = uin
        
        # 为每个 uin 选择最合适的 name
        for uin, names in uin_names.items():
            # 从后往前找第一个不等于uin的 name
            chosen_name = None
            for name in reversed(names):
                if name != str(uin):
                    chosen_name = name
                    break
            
            # 如果所有 name 都等于 uin，使用 sendMemberName
            if chosen_name is None:
                if uin in uin_member_names:
                    chosen_name = uin_member_names[uin]
                elif names:
                    chosen_name = names[-1]  # 兜底：使用最后一个
            
            if chosen_name:
                self.uin_to_name[uin] = chosen_name
        
        # 保存所有历史昵称（用于口头禅过滤）
        self.uin_all_names = dict(uin_names)

    def get_name(self, uin):
        return self.uin_to_name.get(uin, f"未知用户({uin})")

    def analyze(self):
        logger.info(f"📊 开始分析: {self.chat_name}")
        logger.info(f"📝 消息总数: {len(self.messages)}")
        
        logger.info("🧹 预处理文本...")
        self._preprocess_texts()
        
        logger.info("🔤 分析单字独立性...")
        self.single_char_stats = analyze_single_chars(self.cleaned_texts)
        
        logger.info("🔍 新词发现...")
        self._discover_new_words()
        
        logger.info("🔗 词组合并...")
        self._merge_word_pairs()
        
        logger.info("📈 分词统计...")
        self._tokenize_and_count()
        
        logger.info("🎮 趣味统计...")
        self._fun_statistics()
        
        logger.info("🔥 热场/冷场分析...")
        self._analyze_heat()
        
        logger.info("🤝 关系网络分析...")
        self._compute_relationships()
        
        logger.info("📅 年度大事件分析...")
        self._compute_daily_events()
        
        logger.info("💬 口头禅与标点分析...")
        self._compute_pet_phrases()
        self._compute_punctuation_rankings()
        
        logger.info("🧹 过滤整理...")
        self._filter_results()
        
        logger.info("✅ 分析完成!")

    def _preprocess_texts(self):
        """预处理所有文本"""
        skipped = 0
        bot_filtered = 0
        for msg in self.messages:
            # 跳过机器人消息
            if self._is_bot_message(msg):
                bot_filtered += 1
                continue
            
            content = msg.get('content', {})
            text = content.get('text', '') if isinstance(content, dict) else ''
            
            # 过滤撤回消息（格式: "{昵称} 撤回了一条消息"），并提取昵称用于过滤
            if '撤回了一条消息' in text:
                name = text.replace('撤回了一条消息', '').strip()
                if name and len(name) >= 2:
                    self.recall_names.add(name)
                skipped += 1
                continue
            
            cleaned = clean_text(text)
            if cleaned and len(cleaned) >= 1:
                self.cleaned_texts.append(cleaned)
            elif text:
                skipped += 1
        
        if cfg.FILTER_BOT_MESSAGES and bot_filtered > 0:
            logger.debug(f"有效文本: {len(self.cleaned_texts)} 条, 跳过: {skipped} 条, 过滤机器人: {bot_filtered} 条")
        else:
            logger.debug(f"有效文本: {len(self.cleaned_texts)} 条, 跳过: {skipped} 条")

    def _discover_new_words(self):
        """新词发现"""
        ngram_freq = Counter()
        left_neighbors = defaultdict(Counter)
        right_neighbors = defaultdict(Counter)
        total_chars = 0
        
        for text in self.cleaned_texts:
            sentences = re.split(r'[，。！？、；：""''（）\s\n\r,\.!?\(\)]', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 2:
                    continue
                total_chars += len(sentence)
                
                for n in range(2, min(6, len(sentence) + 1)):
                    for i in range(len(sentence) - n + 1):
                        ngram = sentence[i:i+n]
                        # 只跳过纯空格
                        if not ngram.strip():
                            continue
                        ngram_freq[ngram] += 1
                        if i > 0:
                            left_neighbors[ngram][sentence[i-1]] += 1
                        else:
                            left_neighbors[ngram]['<BOS>'] += 1
                        if i + n < len(sentence):
                            right_neighbors[ngram][sentence[i+n]] += 1
                        else:
                            right_neighbors[ngram]['<EOS>'] += 1
        
        for word, freq in ngram_freq.items():
            if freq < cfg.NEW_WORD_MIN_FREQ:
                continue
            
            # 邻接熵
            left_ent = calculate_entropy(left_neighbors[word])
            right_ent = calculate_entropy(right_neighbors[word])
            min_ent = min(left_ent, right_ent)
            if min_ent < cfg.ENTROPY_THRESHOLD:
                continue
            
            # PMI
            min_pmi = float('inf')
            for i in range(1, len(word)):
                left_freq = ngram_freq.get(word[:i], 0)
                right_freq = ngram_freq.get(word[i:], 0)
                if left_freq > 0 and right_freq > 0:
                    pmi = math.log2((freq * total_chars) / (left_freq * right_freq + 1e-10))
                    min_pmi = min(min_pmi, pmi)
            
            if min_pmi == float('inf'):
                min_pmi = 0
            
            if min_pmi < cfg.PMI_THRESHOLD:
                continue
            
            self.discovered_words.add(word)
        
        for word in self.discovered_words:
            jieba.add_word(word, freq=1000)
        
        logger.debug(f"发现 {len(self.discovered_words)} 个新词")

    def _merge_word_pairs(self):
        bigram_counter = Counter()
        word_right_counter = Counter()
        
        for text in self.cleaned_texts:
            words = [w for w in jieba.cut(text) if w.strip()]
            for i in range(len(words) - 1):
                w1, w2 = words[i].strip(), words[i+1].strip()
                if not w1 or not w2:
                    continue
                if re.match(r'^[\d\W]+$', w1) or re.match(r'^[\d\W]+$', w2):
                    continue
                bigram_counter[(w1, w2)] += 1
                word_right_counter[w1] += 1
        
        for (w1, w2), count in bigram_counter.items():
            merged = w1 + w2
            if len(merged) > cfg.MERGE_MAX_LEN:
                continue
            if count < cfg.MERGE_MIN_FREQ:
                continue
            
            # 条件概率 P(w2|w1)
            if word_right_counter[w1] > 0:
                prob = count / word_right_counter[w1]
                if prob >= cfg.MERGE_MIN_PROB:
                    self.merged_words[merged] = (w1, w2, count, prob)
                    jieba.add_word(merged, freq=count * 1000)
        
        logger.debug(f"合并 {len(self.merged_words)} 个词组")
        
        if self.merged_words:
            sorted_merges = sorted(self.merged_words.items(), key=lambda x: -x[1][2])[:10]
            for merged, (w1, w2, cnt, prob) in sorted_merges:
                logger.debug(f"  {merged}: {w1}+{w2} ({cnt}次, {prob:.0%})")

    def _tokenize_and_count(self):
        for idx, msg in enumerate(self.messages):
            if self._is_bot_message(msg):
                continue
            
            sender_uin = msg.get('sender', {}).get('uin')
            content = msg.get('content', {})
            text = content.get('text', '') if isinstance(content, dict) else ''
            original_text = text
            
            # 过滤撤回消息
            if '撤回了一条消息' in text:
                continue
            
            cleaned = clean_text(text)
            
            if not cleaned:
                continue
            
            words = list(jieba.cut(cleaned))
            emojis = extract_emojis(cleaned)
            words = [w for w in words if not is_emoji(w)]  # 新增：从words中去掉emoji
            all_tokens = words + emojis
            
            # 解析日期用于日度词频
            day_key = None
            msg_dt = parse_datetime(msg.get('timestamp', ''))
            if msg_dt is not None:
                day_key = msg_dt.strftime('%Y-%m-%d')
            
            for word in all_tokens:
                word = word.strip()
                if not word:
                    continue
                
                # 提前过滤黑名单（性能优化：避免统计后再过滤）
                if word in cfg.BLACKLIST:
                    continue
                
                self.word_freq[word] += 1
                if sender_uin:
                    self.word_contributors[word][sender_uin] += 1
                    self.user_word_freq[sender_uin][word] += 1
                if day_key and len(word) >= 2 and not is_emoji(word):
                    self.daily_word_freq[day_key][word] += 1
                if len(self.word_samples[word]) < cfg.SAMPLE_COUNT * 3:
                    self.word_samples[word].append(cleaned)

    def _fun_statistics(self):
        """趣味统计"""
        prev_clean = None  
        prev_sender = None
        
        for msg in self.messages:
            if self._is_bot_message(msg):
                continue
            
            sender_uin = msg.get('sender', {}).get('uin')
            if not sender_uin:
                continue
            
            content = msg.get('content', {})
            text = content.get('text', '') if isinstance(content, dict) else ''
            timestamp = msg.get('timestamp', '')
            
            self.user_msg_count[sender_uin] += 1
            clean = clean_text(text)
            self.user_char_count[sender_uin] += len(clean)
            
            # 图片检测（排除gif）
            if '[图片:' in text:
                if '.gif' not in text.lower():
                    self.user_image_count[sender_uin] += 1
            
            # 转发检测
            if '[合并转发:' in text:
                self.user_forward_count[sender_uin] += 1
            
            # 回复统计（使用 content.elements 中的 reply 元素）
            elements = content.get('elements', []) if isinstance(content, dict) else []
            reply_target_uin = None
            for elem in elements:
                if elem.get('type') == 'reply':
                    reply_data = elem.get('data', {})
                    self.user_reply_count[sender_uin] += 1
                    # 优先用 senderUin，其次通过 referencedMessageId 查找
                    target_uin = reply_data.get('senderUin', '')
                    if not target_uin:
                        ref_msg_id = reply_data.get('referencedMessageId')
                        if ref_msg_id and ref_msg_id in self.msgid_to_sender:
                            target_uin = self.msgid_to_sender[ref_msg_id]
                    if target_uin and target_uin != sender_uin:
                        reply_target_uin = target_uin
                        self.user_replied_count[target_uin] += 1
                        self.interaction_graph[sender_uin][target_uin] += 1
                    break
            
            # @统计（使用 content.mentions）
            mentions = content.get('mentions', []) if isinstance(content, dict) else []
            for mention in mentions:
                mention_uid = mention.get('uid', '')
                mention_name = mention.get('name', '')
                if mention_uid and mention_uid != '0':
                    self.user_at_count[sender_uin] += 1
                    target_uin = self.uid_to_uin.get(mention_uid, '')
                    if target_uin:
                        self.user_ated_count[target_uin] += 1
                        if target_uin != sender_uin:
                            self.interaction_graph[sender_uin][target_uin] += 1
                    else:
                        # uid 映射不到时用 name 作为 key 标记
                        self.user_ated_count[mention_name or mention_uid] += 1
            
            # 表情统计（包括emoji、[表情:]、gif）
            emojis = extract_emojis(clean)
            gif_count = text.lower().count('.gif')
            bracket_emoji_count = text.count('[表情:')
            emoji_count = len(emojis) + bracket_emoji_count + gif_count
            if emoji_count > 0:
                self.user_emoji_count[sender_uin] += emoji_count
            
            # 链接统计
            if '[链接:' in text or re.search(r'https?://', text):
                self.user_link_count[sender_uin] += 1
            
            # 时段统计
            hour = parse_timestamp(timestamp)
            if hour is not None:
                self.hour_distribution[hour] += 1
                if hour in cfg.NIGHT_OWL_HOURS:
                    self.user_night_count[sender_uin] += 1
                if hour in cfg.EARLY_BIRD_HOURS:
                    self.user_morning_count[sender_uin] += 1
            
            # 月度/日度统计
            msg_dt = parse_datetime(timestamp)
            if msg_dt is not None:
                month_key = msg_dt.strftime('%Y-%m')
                day_key = msg_dt.strftime('%Y-%m-%d')
                self.month_distribution[month_key] += 1
                self.daily_distribution[day_key] += 1
            
            # 标点统计（用原始文本）
            if text:
                punct = self.user_punctuation[sender_uin]
                punct['exclaim'] += text.count('！') + text.count('!')
                punct['question'] += text.count('？') + text.count('?')
                punct['ellipsis'] += text.count('…') + text.count('...')
                punct['total_chars'] += len(text)
            
            # 复读统计（用清理后文本，且内容要有意义）
            if clean and len(clean) >= 2:
                if clean == prev_clean and sender_uin != prev_sender:
                    self.user_repeat_count[sender_uin] += 1
            
            prev_clean = clean if clean else prev_clean  # 空消息不更新
            prev_sender = sender_uin
        
        # 计算人均字数
        for uin in self.user_msg_count:
            msg_count = self.user_msg_count[uin]
            char_count = self.user_char_count[uin]
            if msg_count >= 10:
                self.user_char_per_msg[uin] = char_count / msg_count

    def _analyze_heat(self):
        """热场王/冷场王：统计每人发言后5分钟内的他人消息量（滑动窗口O(n)）"""
        from datetime import timedelta
        timed_msgs = []
        for msg in self.messages:
            if self._is_bot_message(msg):
                continue
            sender_uin = msg.get('sender', {}).get('uin')
            if not sender_uin:
                continue
            dt = parse_datetime(msg.get('timestamp', ''))
            if dt is None:
                continue
            timed_msgs.append((dt, sender_uin))

        timed_msgs.sort(key=lambda x: x[0])
        window = timedelta(minutes=5)
        n = len(timed_msgs)
        right = 0
        window_counter = Counter()
        window_total = 0

        for i in range(n):
            msg_dt, sender_uin = timed_msgs[i]
            while right < n and timed_msgs[right][0] - msg_dt <= window:
                window_counter[timed_msgs[right][1]] += 1
                window_total += 1
                right += 1
            others = window_total - window_counter.get(sender_uin, 0)
            self.user_heat_scores[sender_uin].append(others)
            window_counter[sender_uin] -= 1
            window_total -= 1

    def _compute_relationships(self):
        """最佳拍档 / 单向奔赴（基于互动关系图）"""
        all_pairs = set()
        for sender, targets in self.interaction_graph.items():
            for target in targets:
                if sender != target:
                    all_pairs.add(tuple(sorted([sender, target])))

        best_pairs = []
        one_sided = []
        for a, b in all_pairs:
            a_to_b = self.interaction_graph[a].get(b, 0)
            b_to_a = self.interaction_graph[b].get(a, 0)
            total = a_to_b + b_to_a
            if total < 5:
                continue
            best_pairs.append((a, b, total, a_to_b, b_to_a))
            # 单向奔赴：一方互动远多于另一方
            if a_to_b > 0 and b_to_a > 0:
                ratio = max(a_to_b, b_to_a) / min(a_to_b, b_to_a)
                if ratio >= 3 and max(a_to_b, b_to_a) >= 10:
                    active = a if a_to_b > b_to_a else b
                    passive = b if a_to_b > b_to_a else a
                    one_sided.append((active, passive, max(a_to_b, b_to_a), min(a_to_b, b_to_a), ratio))
            elif a_to_b >= 10 and b_to_a == 0:
                one_sided.append((a, b, a_to_b, 0, 999.0))
            elif b_to_a >= 10 and a_to_b == 0:
                one_sided.append((b, a, b_to_a, 0, 999.0))

        best_pairs.sort(key=lambda x: x[2], reverse=True)
        one_sided.sort(key=lambda x: x[4], reverse=True)
        self.best_pairs = best_pairs[:10]
        self.one_sided_relationships = one_sided[:10]

    def _compute_daily_events(self):
        """年度大事件：消息量突增的日期 + 当天突增热词（按突增度排序）"""
        if len(self.daily_distribution) < 3:
            self.daily_events = []
            return
        counts = list(self.daily_distribution.values())
        mean = sum(counts) / len(counts)
        std = (sum((c - mean) ** 2 for c in counts) / len(counts)) ** 0.5
        threshold = max(mean + 1.5 * std, mean * 1.5)
        total_days = len(self.daily_distribution)

        events = []
        for day, count in self.daily_distribution.items():
            if count < threshold:
                continue
            # 计算每个词的突增度 = 当天次数 / (全年日均次数 + 平滑项)
            day_words = self.daily_word_freq.get(day, Counter())
            scored = []
            for word, day_count in day_words.items():
                if word in CHINESE_STOPWORDS or word in cfg.BLACKLIST:
                    continue
                if len(word) < 2 or is_emoji(word):
                    continue
                global_count = self.word_freq.get(word, 0)
                daily_avg = global_count / total_days if total_days > 0 else 0
                boost = day_count / (daily_avg + 0.5)
                scored.append((word, day_count, boost))
            # 按突增度排序，取Top5
            scored.sort(key=lambda x: x[2], reverse=True)
            top_words = [w for w, _, _ in scored[:5]]
            if top_words:
                events.append({
                    'date': day,
                    'count': count,
                    'top_words': top_words
                })
        events.sort(key=lambda x: x['count'], reverse=True)
        self.daily_events = events[:5]

    def _compute_pet_phrases(self):
        """口头禅：每人最高频的特色词汇（按使用次数 × 个人特色度加权排序）"""
        # 构建用户名过滤集合（所有历史昵称 + 撤回消息昵称 + jieba分词结果），避免用户名被统计为口头禅
        name_filter = set()
        for names in self.uin_all_names.values():
            for name in names:
                if not name or len(name) < 2:
                    continue
                name_filter.add(name)
                for seg in jieba.lcut(name):
                    if len(seg) >= 2:
                        name_filter.add(seg)
        # 撤回消息中的昵称（如"一只奇美拉"）
        for name in self.recall_names:
            name_filter.add(name)
            for seg in jieba.lcut(name):
                if len(seg) >= 2:
                    name_filter.add(seg)

        self.pet_phrases = {}
        for uin, word_freq in self.user_word_freq.items():
            if self.user_msg_count.get(uin, 0) < 20:
                continue
            candidates = []
            for word, count in word_freq.most_common(100):
                if word in CHINESE_STOPWORDS or word in cfg.BLACKLIST:
                    continue
                if word in name_filter:
                    continue
                if len(word) < 2:
                    continue
                total_in_group = self.word_freq.get(word, 0)
                ratio = count / total_in_group if total_in_group > 0 else 0
                # 综合得分：使用次数 × (个人占比 + 平滑项)，兼顾高频和特色
                score = count * (ratio + 0.3)
                candidates.append((word, count, ratio, score))
            # 按综合得分排序
            candidates.sort(key=lambda x: x[3], reverse=True)
            if candidates:
                self.pet_phrases[uin] = [
                    {'word': w, 'count': c, 'ratio': round(r, 3)}
                    for w, c, r, _ in candidates[:5]
                ]

    def _compute_punctuation_rankings(self):
        """标点狂魔排行"""
        exclaim_rank = Counter()
        question_rank = Counter()
        ellipsis_rank = Counter()
        for uin, punct in self.user_punctuation.items():
            if self.user_msg_count.get(uin, 0) < 10:
                continue
            exclaim_rank[uin] = punct['exclaim']
            question_rank[uin] = punct['question']
            ellipsis_rank[uin] = punct['ellipsis']
        self.punctuation_rankings = {
            'exclaim': exclaim_rank.most_common(10),
            'question': question_rank.most_common(10),
            'ellipsis': ellipsis_rank.most_common(10),
        }

    def _filter_results(self):
        """过滤结果"""
        filtered_freq = Counter()
        
        for word, freq in self.word_freq.items():
            if len(word) < cfg.MIN_WORD_LEN or len(word) > cfg.MAX_WORD_LEN:
                continue
            if freq < cfg.MIN_FREQ:
                continue
            
            if word in cfg.WHITELIST:
                filtered_freq[word] = freq
                continue
            
            if word in cfg.BLACKLIST:
                continue
            
            # 单字特殊处理
            if len(word) == 1:
                if is_emoji(word):
                    pass  # emoji保留
                else:
                    # 单个符号跳过（但数字/字母走单字统计）
                    if word in string.punctuation or word in '，。！？；：、""''（）【】':
                        continue
                    # 其他单字（数字/字母/汉字）走独立性检查
                    stats = self.single_char_stats.get(word)
                    if stats:
                        total, indep, ratio = stats
                        if ratio < cfg.SINGLE_MIN_SOLO_RATIO or indep < cfg.SINGLE_MIN_SOLO_COUNT:
                            continue
                    else:
                        continue
                        
            filtered_freq[word] = freq
        
        self.word_freq = filtered_freq
        
        # 采样
        for word in self.word_samples:
            samples = self.word_samples[word]
            if len(samples) > cfg.SAMPLE_COUNT:
                self.word_samples[word] = random.sample(samples, cfg.SAMPLE_COUNT)
        
        logger.debug(f"过滤后 {len(self.word_freq)} 个词")

    def get_top_words(self, n=None):
        n = n or cfg.TOP_N
        return self.word_freq.most_common(n)

    def get_word_detail(self, word):
        return {
            'word': word,
            'freq': self.word_freq.get(word, 0),
            'samples': self.word_samples.get(word, []),
            'contributors': [(self.get_name(uin), count) 
                           for uin, count in self.word_contributors[word].most_common(cfg.CONTRIBUTOR_TOP_N)]
        }

    def get_fun_rankings(self):
        rankings = {}
        
        def fmt(counter, top_n=cfg.RANK_TOP_N):
            return [(self.get_name(uin), count) for uin, count in counter.most_common(top_n)]
        
        rankings['话痨榜'] = fmt(self.user_msg_count)
        rankings['字数榜'] = fmt(self.user_char_count)
        
        sorted_avg = sorted(self.user_char_per_msg.items(), key=lambda x: x[1], reverse=True)[:cfg.RANK_TOP_N]
        rankings['长文王'] = [(self.get_name(uin), f"{avg:.1f}字/条") for uin, avg in sorted_avg]
        
        rankings['图片狂魔'] = fmt(self.user_image_count)
        rankings['合并转发王'] = fmt(self.user_forward_count)
        rankings['回复狂'] = fmt(self.user_reply_count)
        rankings['被回复最多'] = fmt(self.user_replied_count)
        rankings['艾特狂'] = fmt(self.user_at_count)
        rankings['被艾特最多'] = fmt(self.user_ated_count)
        rankings['表情帝'] = fmt(self.user_emoji_count)
        rankings['链接分享王'] = fmt(self.user_link_count)
        rankings['深夜党'] = fmt(self.user_night_count)
        rankings['早起鸟'] = fmt(self.user_morning_count)
        rankings['复读机'] = fmt(self.user_repeat_count)
        
        return rankings
    
    def export_json(self):
        """导出JSON格式结果（包含uin信息）"""
        result = {
            'chatName': self.chat_name,
            'messageCount': len(self.messages),
            'topWords': [
                {
                    'word': word,
                    'freq': freq,
                    'contributors': [
                        {
                            'name': self.get_name(uin), 
                            'uin': uin,
                            'count': count
                        }
                        for uin, count in self.word_contributors[word].most_common(cfg.CONTRIBUTOR_TOP_N)
                    ],
                    'samples': self.word_samples.get(word, [])[:cfg.SAMPLE_COUNT]
                }
                for word, freq in self.get_top_words()
            ],
            'rankings': {},
            'hourDistribution': {str(h): self.hour_distribution.get(h, 0) for h in range(24)}
        }
        
        # 趣味榜单（包含uin）
        def fmt_with_uin(counter, top_n=cfg.RANK_TOP_N):
            return [
                {'name': self.get_name(uin), 'uin': uin, 'value': count}
                for uin, count in counter.most_common(top_n)
            ]
        
        result['rankings']['话痨榜'] = fmt_with_uin(self.user_msg_count)
        result['rankings']['字数榜'] = fmt_with_uin(self.user_char_count)
        
        # 长文王特殊处理
        sorted_avg = sorted(self.user_char_per_msg.items(), key=lambda x: x[1], reverse=True)[:cfg.RANK_TOP_N]
        result['rankings']['长文王'] = [
            {'name': self.get_name(uin), 'uin': uin, 'value': f"{avg:.1f}字/条"}
            for uin, avg in sorted_avg
        ]
        
        result['rankings']['图片狂魔'] = fmt_with_uin(self.user_image_count)
        result['rankings']['合并转发王'] = fmt_with_uin(self.user_forward_count)
        result['rankings']['回复狂'] = fmt_with_uin(self.user_reply_count)
        result['rankings']['被回复最多'] = fmt_with_uin(self.user_replied_count)
        result['rankings']['艾特狂'] = fmt_with_uin(self.user_at_count)
        result['rankings']['被艾特最多'] = fmt_with_uin(self.user_ated_count)
        result['rankings']['表情帝'] = fmt_with_uin(self.user_emoji_count)
        result['rankings']['链接分享王'] = fmt_with_uin(self.user_link_count)
        result['rankings']['深夜党'] = fmt_with_uin(self.user_night_count)
        result['rankings']['早起鸟'] = fmt_with_uin(self.user_morning_count)
        result['rankings']['复读机'] = fmt_with_uin(self.user_repeat_count)
        
        # ===== 新增维度输出 =====
        
        # 热场王/冷场王
        heat_avg = {}
        for uin, scores in self.user_heat_scores.items():
            if scores and len(scores) >= 10:
                heat_avg[uin] = sum(scores) / len(scores)
        sorted_heat = sorted(heat_avg.items(), key=lambda x: x[1], reverse=True)
        result['heatKing'] = [
            {'name': self.get_name(uin), 'uin': uin, 'avg_after': round(avg, 2)}
            for uin, avg in sorted_heat[:10]
        ]
        result['coldKing'] = [
            {'name': self.get_name(uin), 'uin': uin, 'avg_after': round(avg, 2)}
            for uin, avg in sorted_heat[-10:][::-1] if heat_avg.get(uin, 0) >= 0
        ]
        
        # 互动关系图谱（节点 + 边）
        nodes = []
        node_set = set()
        edges = []
        for sender, targets in self.interaction_graph.items():
            for target, weight in targets.items():
                if sender == target or weight < 3:
                    continue
                node_set.add(sender)
                node_set.add(target)
                edges.append({'source': sender, 'target': target, 'weight': weight})
        for uin in node_set:
            nodes.append({
                'id': uin,
                'name': self.get_name(uin),
                'msgCount': self.user_msg_count.get(uin, 0)
            })
        result['interactionGraph'] = {'nodes': nodes, 'edges': edges}
        
        # 月度活跃分布
        result['monthDistribution'] = dict(sorted(self.month_distribution.items()))
        
        # 年度大事件
        result['dailyEvents'] = getattr(self, 'daily_events', [])
        
        # 口头禅
        result['petPhrases'] = {
            uin: phrases for uin, phrases in getattr(self, 'pet_phrases', {}).items()
        }
        
        # 标点狂魔
        punct = getattr(self, 'punctuation_rankings', {})
        result['punctuationRankings'] = {
            'exclaim': [{'name': self.get_name(u), 'uin': u, 'value': c} for u, c in punct.get('exclaim', [])],
            'question': [{'name': self.get_name(u), 'uin': u, 'value': c} for u, c in punct.get('question', [])],
            'ellipsis': [{'name': self.get_name(u), 'uin': u, 'value': c} for u, c in punct.get('ellipsis', [])],
        }
        
        # 最佳拍档
        result['bestPairs'] = [
            {
                'a': {'name': self.get_name(a), 'uin': a},
                'b': {'name': self.get_name(b), 'uin': b},
                'total': total,
                'a_to_b': a2b,
                'b_to_a': b2a
            }
            for a, b, total, a2b, b2a in getattr(self, 'best_pairs', [])
        ]
        
        # 单向奔赴
        result['oneSided'] = [
            {
                'active': {'name': self.get_name(a), 'uin': a},
                'passive': {'name': self.get_name(b), 'uin': b},
                'active_count': ac,
                'passive_count': pc,
                'ratio': round(r, 1)
            }
            for a, b, ac, pc, r in getattr(self, 'one_sided_relationships', [])
        ]
        
        return result

"""
单词表数据清洗模块
专门用于清洗和验证单词表数据，确保英文单词和中文释义的严格分离
"""

import re
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class VocabularyCleaner:
    """单词表数据清洗器"""
    
    # 英文单词正则表达式（允许连字符和撇号）
    ENGLISH_WORD_PATTERN = re.compile(r'^[a-zA-Z\-\']+$')
    
    # 中文释义正则表达式（允许中文、标点符号和空格）
    CHINESE_DEFINITION_PATTERN = re.compile(r'^[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\s，。；：！？、（）【】《》]+$')
    
    # 词性标签映射
    POS_MAPPING = {
        # 标准词性标签
        'n': 'noun', 'noun': 'noun', '名词': 'noun',
        'v': 'verb', 'verb': 'verb', '动词': 'verb',
        'adj': 'adjective', 'adjective': 'adjective', '形容词': 'adjective',
        'adv': 'adverb', 'adverb': 'adverb', '副词': 'adverb',
        'prep': 'preposition', 'preposition': 'preposition', '介词': 'preposition',
        'conj': 'conjunction', 'conjunction': 'conjunction', '连词': 'conjunction',
        'pron': 'pronoun', 'pronoun': 'pronoun', '代词': 'pronoun',
        'interj': 'interjection', 'interjection': 'interjection', '感叹词': 'interjection',
        'art': 'article', 'article': 'article', '冠词': 'article',
        'num': 'numeral', 'numeral': 'numeral', '数词': 'numeral',
        
        # 常见缩写
        'n.': 'noun', 'v.': 'verb', 'adj.': 'adjective', 'adv.': 'adverb',
        'prep.': 'preposition', 'conj.': 'conjunction', 'pron.': 'pronoun',
        'interj.': 'interjection', 'art.': 'article', 'num.': 'numeral'
    }
    
    @classmethod
    def clean_word_data(cls, word_data: Dict[str, str]) -> Dict[str, str]:
        """
        清洗单个单词数据
        
        Args:
            word_data: 包含word, definition, part_of_speech的字典
            
        Returns:
            清洗后的单词数据
        """
        cleaned = {
            'word': '',
            'definition': '',
            'part_of_speech': '',
            'example': word_data.get('example', '')
        }
        
        # 清洗单词
        word = word_data.get('word', '').strip()
        if word:
            cleaned['word'] = cls._clean_word(word)
        
        # 清洗释义
        definition = word_data.get('definition', '').strip()
        if definition:
            cleaned['definition'] = cls._clean_definition(definition)
        
        # 清洗词性
        part_of_speech = word_data.get('part_of_speech', '').strip()
        if part_of_speech:
            cleaned['part_of_speech'] = cls._clean_part_of_speech(part_of_speech)
        
        return cleaned
    
    @classmethod
    def _clean_word(cls, word: str) -> str:
        """清洗英文单词"""
        # 去除多余空格
        word = word.strip()
        
        # 检查是否为纯英文单词
        if cls.ENGLISH_WORD_PATTERN.match(word):
            return word
        
        # 尝试提取英文部分
        # 处理可能包含数字或特殊字符的情况
        english_parts = re.findall(r'[a-zA-Z\-\']+', word)
        if english_parts:
            # 取最长的英文部分
            return max(english_parts, key=len)
        
        # 如果无法提取英文，返回空字符串
        logger.warning(f"无法提取有效英文单词: {word}")
        return ''
    
    @classmethod
    def _clean_definition(cls, definition: str) -> str:
        """清洗中文释义"""
        # 去除多余空格
        definition = definition.strip()
        
        # 检查是否为纯中文释义
        if cls.CHINESE_DEFINITION_PATTERN.match(definition):
            return definition
        
        # 尝试提取中文部分
        chinese_parts = re.findall(r'[\u4e00-\u9fff]+', definition)
        if chinese_parts:
            # 合并所有中文部分
            return ''.join(chinese_parts)
        
        # 如果无法提取中文，返回空字符串
        logger.warning(f"无法提取有效中文释义: {definition}")
        return ''
    
    @classmethod
    def _clean_part_of_speech(cls, pos: str) -> str:
        """清洗词性标签"""
        # 去除多余空格
        pos = pos.strip().lower()
        
        # 检查是否为标准词性标签
        if pos in cls.POS_MAPPING:
            return cls.POS_MAPPING[pos]
        
        # 尝试匹配标准词性
        for key, value in cls.POS_MAPPING.items():
            if key in pos:
                return value
        
        # 如果无法识别，返回原始值
        return pos
    
    @classmethod
    def validate_word_data(cls, word_data: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        验证单词数据的有效性
        
        Args:
            word_data: 单词数据
            
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        # 检查单词
        word = word_data.get('word', '').strip()
        if not word:
            errors.append("单词不能为空")
        elif not cls.ENGLISH_WORD_PATTERN.match(word):
            errors.append(f"单词 '{word}' 包含非英文字符")
        
        # 检查释义
        definition = word_data.get('definition', '').strip()
        if not definition:
            errors.append("释义不能为空")
        elif not cls.CHINESE_DEFINITION_PATTERN.match(definition):
            errors.append(f"释义 '{definition}' 包含非中文字符")
        
        # 检查词性
        part_of_speech = word_data.get('part_of_speech', '').strip()
        if part_of_speech and part_of_speech not in cls.POS_MAPPING.values():
            # 只警告，不视为错误
            logger.warning(f"非标准词性标签: {part_of_speech}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def clean_vocabulary_list(cls, vocabulary_list: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        清洗整个单词表
        
        Args:
            vocabulary_list: 原始单词表数据
            
        Returns:
            (清洗后的有效单词列表, 无效单词列表)
        """
        valid_words = []
        invalid_words = []
        
        for i, word_data in enumerate(vocabulary_list):
            # 清洗数据
            cleaned_data = cls.clean_word_data(word_data)
            
            # 验证数据
            is_valid, errors = cls.validate_word_data(cleaned_data)
            
            if is_valid and cleaned_data['word'] and cleaned_data['definition']:
                valid_words.append(cleaned_data)
            else:
                invalid_words.append({
                    'original_data': word_data,
                    'cleaned_data': cleaned_data,
                    'errors': errors,
                    'index': i
                })
        
        return valid_words, invalid_words
    
    @classmethod
    def parse_text_content(cls, content: str, file_extension: str) -> List[Dict[str, str]]:
        """
        解析文本内容为单词表数据
        
        Args:
            content: 文本内容
            file_extension: 文件扩展名
            
        Returns:
            解析后的单词表数据
        """
        words = []
        
        if file_extension == 'txt':
            # TXT格式：每行一个单词或单词\t释义\t词性\t例句
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                if line.strip():
                    parts = line.strip().split('\t')
                    word_data = {
                        'word': parts[0] if len(parts) > 0 else "",
                        'definition': parts[1] if len(parts) > 1 else "",
                        'part_of_speech': parts[2] if len(parts) > 2 else "",
                        'example': parts[3] if len(parts) > 3 else ""
                    }
                    words.append(word_data)
        
        elif file_extension == 'csv':
            # CSV格式：单词,释义,词性,例句
            import csv
            from io import StringIO
            
            reader = csv.reader(StringIO(content))
            for row_num, row in enumerate(reader, 1):
                if row and row[0].strip():
                    word_data = {
                        'word': row[0].strip() if len(row) > 0 else "",
                        'definition': row[1].strip() if len(row) > 1 else "",
                        'part_of_speech': row[2].strip() if len(row) > 2 else "",
                        'example': row[3].strip() if len(row) > 3 else ""
                    }
                    words.append(word_data)
        
        return words
    
    @classmethod
    def generate_cleaning_report(cls, valid_words: List[Dict[str, str]], invalid_words: List[Dict[str, str]]) -> Dict[str, any]:
        """
        生成清洗报告
        
        Args:
            valid_words: 有效单词列表
            invalid_words: 无效单词列表
            
        Returns:
            清洗报告
        """
        return {
            'total_words': len(valid_words) + len(invalid_words),
            'valid_words_count': len(valid_words),
            'invalid_words_count': len(invalid_words),
            'valid_words': valid_words,
            'invalid_words': invalid_words,
            'cleaning_rate': len(valid_words) / (len(valid_words) + len(invalid_words)) if (len(valid_words) + len(invalid_words)) > 0 else 0
        }


# 使用示例
if __name__ == "__main__":
    # 测试数据
    test_data = [
        {'word': 'hello123', 'definition': '你好', 'part_of_speech': 'n.'},
        {'word': 'good', 'definition': '好的', 'part_of_speech': 'adj'},
        {'word': 'time', 'definition': '时间 123', 'part_of_speech': 'noun'},
        {'word': '123day', 'definition': '天，日', 'part_of_speech': '名词'},
        {'word': 'computer', 'definition': '电脑', 'part_of_speech': 'n'},
    ]
    
    # 清洗数据
    valid, invalid = VocabularyCleaner.clean_vocabulary_list(test_data)
    
    print("=== 清洗结果 ===")
    print(f"有效单词: {len(valid)} 个")
    print(f"无效单词: {len(invalid)} 个")
    
    print("\n=== 有效单词 ===")
    for word in valid:
        print(f"{word['word']} - {word['definition']} ({word['part_of_speech']})")
    
    print("\n=== 无效单词 ===")
    for invalid_word in invalid:
        print(f"原始: {invalid_word['original_data']}")
        print(f"清洗后: {invalid_word['cleaned_data']}")
        print(f"错误: {invalid_word['errors']}")
        print("---")
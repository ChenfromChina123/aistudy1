#!/usr/bin/env python3
"""
使用AI生成预设单词并添加到公共单词库
运行方式：python py/generate_preset_words.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入数据库相关
from language_learning import init_all_preset_words, generate_preset_words_with_ai
from app import SessionLocal
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    print("=" * 60)
    print("AI生成预设单词工具")
    print("=" * 60)
    print()
    
    # 获取数据库会话
    db = SessionLocal()
    
    try:
        # 询问用户要执行的操作
        print("请选择操作：")
        print("1. 生成所有标签的单词（四级、六级、托福、雅思、考研、GRE、SAT）")
        print("2. 生成指定标签的单词")
        print("3. 退出")
        print()
        
        choice = input("请输入选项（1-3）: ").strip()
        
        if choice == "1":
            print("\n开始生成所有标签的单词...")
            print("注意：这可能需要一些时间，请耐心等待...")
            print()
            init_all_preset_words(db)
            print("\n所有标签的单词生成完成！")
            
        elif choice == "2":
            print("\n可用的标签：")
            tags = ["四级", "六级", "托福", "雅思", "考研", "GRE", "SAT"]
            for i, tag in enumerate(tags, 1):
                print(f"{i}. {tag}")
            print()
            
            tag_choice = input("请输入标签名称或序号: ").strip()
            
            # 检查是否是序号
            if tag_choice.isdigit() and 1 <= int(tag_choice) <= len(tags):
                tag = tags[int(tag_choice) - 1]
            else:
                tag = tag_choice
            
            if tag not in tags:
                print(f"错误：无效的标签 '{tag}'")
                return
            
            count_input = input(f"请输入要为标签'{tag}'生成的单词数量（默认500）: ").strip()
            count = int(count_input) if count_input.isdigit() else 500
            
            print(f"\n开始为标签'{tag}'生成{count}个单词...")
            print("注意：这可能需要一些时间，请耐心等待...")
            print()
            generate_preset_words_with_ai(db, tag, count, 'en')
            print(f"\n标签'{tag}'的单词生成完成！")
            
        elif choice == "3":
            print("退出")
            return
        else:
            print(f"错误：无效的选项 '{choice}'")
            return
            
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        logger.error(f"执行失败: {str(e)}", exc_info=True)
        print(f"\n错误：{str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    main()


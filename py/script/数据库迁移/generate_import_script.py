#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成导入脚本工具
用于为已导出的数据生成导入脚本

使用方法:
    python generate_import_script.py --data-dir <数据目录> --target-db <目标数据库URL>
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / 'py'))


def generate_import_script(data_dir: Path, target_db_url: str, output_script: Path):
    """生成导入脚本"""
    script_content = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
自动生成的数据库导入脚本
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
数据目录: {data_dir}
目标数据库: {target_db_url.split('@')[-1] if '@' in target_db_url else 'N/A'}
\"\"\"

import sys
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / 'py'))

from script.数据库迁移.migrate_all_data import DataImporter

if __name__ == "__main__":
    data_dir = Path(r"{data_dir}")
    target_db_url = r"{target_db_url}"
    
    print("=" * 80)
    print("开始导入数据")
    print(f"数据目录: {{data_dir}}")
    print(f"目标数据库: {{target_db_url.split('@')[-1] if '@' in target_db_url else 'N/A'}}")
    print("=" * 80)
    
    importer = DataImporter(target_db_url, data_dir)
    importer.import_all()
    print("\\n✓ 数据导入完成！")
"""
    
    output_script.write_text(script_content, encoding='utf-8')
    # 在Unix系统上添加执行权限
    import os
    if os.name != 'nt':
        os.chmod(output_script, 0o755)
    
    print(f"✓ 导入脚本已生成: {output_script}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成数据库导入脚本')
    parser.add_argument(
        '--data-dir',
        type=str,
        required=True,
        help='数据文件目录（包含SQL文件的目录）'
    )
    parser.add_argument(
        '--target-db',
        type=str,
        required=True,
        help='目标数据库连接URL'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='输出脚本文件名（默认: <data_dir>/import_data.py）'
    )
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"错误: 数据目录不存在: {data_dir}")
        sys.exit(1)
    
    if args.output:
        output_script = Path(args.output)
    else:
        output_script = data_dir / 'import_data.py'
    
    generate_import_script(data_dir, args.target_db, output_script)
    print(f"\n使用生成的脚本导入数据:")
    print(f"python {output_script}")


if __name__ == "__main__":
    main()


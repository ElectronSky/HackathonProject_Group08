# hackathon_project/__main__.py
# 项目统一入口点，支持 python -m hackathon_project 运行

import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径（只在入口处设置一次）
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 现在可以安全地导入项目内任何模块
from app import main as run_app

if __name__ == "__main__":
    run_app()
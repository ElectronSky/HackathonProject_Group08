# 年轻人财商记账助手

**Hackathon Agent/Coding 赛道参赛作品**

一个面向16-25岁年轻人的AI记账应用，通过行为习惯养成推动财商启蒙。

---

## 产品演示亮点

### 智能记账
用户输入自然语言消费描述，AI自动识别类别、金额、时间并记录
- 输入："今天中午吃了碗面花了15块"
- 输出：已自动归类到"餐饮"，记录完成

### 财商分析助手
分析消费模式，识别问题，提供可执行建议
- 消费概览：总支出、类别占比、日均消费
- 问题识别：高频小额支出、预算超支等
- 可执行建议：具体行动方案（如"每周奶茶限制2次，月预算不超过200元"）

### 知识卡片系统
基于分析推荐财商知识，形成学习闭环
- 分析后推荐1张最相关的学习卡片
- 设置观察周期，评估执行效果
- 追踪改善情况

### 积分激励系统
记账行为获得积分，兑换优惠券
- 每日记账、连续打卡获得积分
- 积分兑换商家优惠券

---

## 技术架构

### Agent系统
```
ReAct架构：理解 -> 规划 -> 工具调用 -> 执行 -> 反思
```

**双Agent协作：**
- 记账Agent：自然语言记账、收入记录
- 财商分析Agent：消费分析、问题识别、卡片推荐

**中间件能力：**
- 工具调用监控
- Prompt动态切换
- 模型异常自动降级

### 工具调用链
| 工具 | 功能 |
|------|------|
| get_current_time | 获取系统时间用于时间推理 |
| build_finance_evidence_pack | 构建结构化数据分析包 |
| rag_summarize | 检索财商知识支撑建议 |
| record_expense | 写入消费记录 |
| fill_context_for_report | 触发报告模式切换 |

### 数据层
- 本地JSON持久化
- 消费记录、预算、储蓄、用户画像独立管理
- 对话历史分场景存储

---

## Agent能力亮点

### 1. 多步规划能力
- 用户输入 -> 时间语义理解 -> 数据查询 -> 分析 -> 报告生成
- 支持相对时间理解（"上个月"、"最近7天"）
- 支持多问题智能拆分与并行分析

### 2. 自我纠错能力
- 模型异常自动降级，页面不崩溃
- 数据不足时的保守回复
- 空结果时的友好提示

### 3. 结构化证据包
- 底层统计：类别占比、时间趋势、金额分布
- 摘要层：交易笔数、总支出、高频类别
- 问题信号：自动识别消费问题

---

## 快速开始

### 环境要求
- Python 3.10+
- 阿里云DashScope API Key

### 安装依赖
```bash
pip install streamlit langchain langchain-community
```

### 运行
```bash
cd hackathon_project
streamlit run app.py
```

### 配置
```bash
export DASHSCOPE_API_KEY="your-api-key"
```

---

## 项目结构

```
hackathon_project/
├── app.py                      # Streamlit主入口
├── agent/                      # Agent核心系统
│   ├── react_agent.py          # 记账Agent
│   ├── finance_react_agent.py  # 财商分析Agent
│   ├── middleware.py           # 中间件
│   └── tools/                   # Agent工具集
├── pages/                       # 页面模块
│   ├── _ai_finance_page.py     # 财商助手
│   ├── _ledger_page.py         # 账本
│   ├── _budget_page.py         # 预算管理
│   ├── _accounts_page.py       # 账户管理
│   ├── _knowledge_cards_page.py # 知识卡片
│   ├── _points_mall_page.py    # 积分商城
│   └── _settings_page.py       # 设置
├── utils/                       # 工具层
│   ├── data_handler.py         # 数据处理
│   ├── evidence_pack_builder.py # 证据包构建
│   ├── card_state_manager.py   # 卡片状态管理
│   ├── card_candidate_builder.py # 卡片候选筛选
│   ├── account_manager.py      # 账户管理
│   ├── income_manager.py       # 收入管理
│   ├── points_manager.py       # 积分管理
│   ├── coupon_repository.py    # 优惠券仓库
│   ├── user_profile_manager.py # 用户画像
│   └── conversation_manager.py # 对话历史
├── prompts/                     # 提示词模板
│   ├── main_prompt.txt         # 记账Agent提示词
│   ├── finance_agent_prompt.txt # 财商Agent提示词
│   ├── finance_report_prompt.txt # 报告提示词
│   ├── card_recommendation_prompt.txt # 卡片推荐
│   └── card_evaluation_prompt.txt # 卡片评估
├── config/                      # 配置文件
│   ├── prompts.yml
│   ├── categories.yml
│   ├── agent.yml
│   ├── budget.yml
│   └── rag.yml
├── model/                       # 模型配置
│   └── factory.py               # 模型工厂
├── rag/                         # RAG知识库
│   ├── rag_service.py
│   └── vector_store.py
├── data/                        # 数据存储
│   ├── users/                   # 用户数据
│   ├── conversations/           # 对话历史
│   ├── knowledge/              # 知识数据
│   ├── rewards/                # 奖励数据
│   └── points/                 # 积分数据
└── logs/                        # 日志文件
```

---

## 评分维度

| 维度 | 分值 | 说明 |
|------|------|------|
| 工程完整度 | 15分 | GitHub结构、README、答辩准备 |
| 产品体验 | 20分 | Demo流畅、用户旅程、交互自然 |
| Agent能力 | 20分 | 多步规划、工具调用、自我纠错 |

---

## 团队分工

- 架构设计：Agent系统设计、中间件开发
- 前端开发：Streamlit页面开发、交互优化
- 数据工程：RAG知识库、证据包构建
- 产品设计：用户画像、知识卡片设计

---

## 未来规划

- 用户画像驱动的个性化语气
- 周报/月报生成与导出
- 社群系统与省钱妙招分享
- 积分商城扩展

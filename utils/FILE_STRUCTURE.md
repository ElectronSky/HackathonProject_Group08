# 项目文件结构说明

> 最后更新：2026-03-29

## 目录结构总览

```
hackathon_project/
├── app.py                          # Streamlit主入口
├── README.md                        # 项目说明文档
├── FILE_STRUCTURE.md                # 本文件，文件路径说明
│
├── agent/                           # Agent核心系统
│   ├── __init__.py
│   ├── react_agent.py               # 记账Agent（自然语言记账入口）
│   ├── finance_react_agent.py       # 财商分析Agent（消费分析入口）
│   ├── middleware.py                # 中间件（工具监控、prompt切换）
│   └── tools/                        # Agent工具集（运行时动态导入）
│
├── pages/                           # Streamlit页面模块
│   ├── __init__.py
│   ├── _ai_finance_page.py          # 财商助手页面
│   ├── _ledger_page.py              # 账本页面
│   ├── _budget_page.py              # 预算管理页面
│   ├── _accounts_page.py             # 账户管理页面
│   ├── _knowledge_cards_page.py       # 知识卡片页面
│   ├── _points_mall_page.py         # 积分商城页面
│   └── _settings_page.py            # 设置页面
│
├── utils/                           # 工具层
│   ├── __init__.py
│   ├── data_handler.py              # 消费数据处理
│   ├── evidence_pack_builder.py      # 结构化证据包构建
│   ├── card_state_manager.py        # 卡片状态管理
│   ├── card_candidate_builder.py     # 卡片候选筛选
│   ├── card_repository.py           # 卡片仓库
│   ├── account_manager.py           # 账户管理
│   ├── income_manager.py            # 收入管理
│   ├── points_manager.py            # 积分管理
│   ├── coupon_repository.py         # 优惠券仓库
│   ├── user_profile_manager.py      # 用户画像管理
│   ├── conversation_manager.py      # 对话历史管理
│   ├── category_service.py          # 类别服务
│   ├── config_handler.py            # 配置处理器
│   ├── finance_analysis_service.py  # 财商分析服务
│   ├── finance_time_parser.py       # 时间解析
│   ├── analysis_query_parser.py     # 分析查询解析
│   ├── prompt_loader.py            # 提示词加载器
│   ├── model_error_helper.py        # 模型异常处理
│   ├── file_handler.py              # 文件处理
│   ├── file_history_store.py        # 文件历史存储
│   ├── path_tools.py                # 路径工具
│   ├── logger_handler.py            # 日志处理
│   └── generate_mock_data.py        # 测试数据生成
│
├── prompts/                         # 提示词模板
│   ├── main_prompt.txt              # 记账Agent主提示词
│   ├── finance_agent_prompt.txt     # 财商Agent主提示词
│   ├── finance_report_prompt.txt    # 财商报告提示词
│   ├── finance_analysis_prompt.txt  # 财商分析提示词
│   ├── finance_quick_advice_prompt.txt # 快速建议提示词
│   ├── finance_time_parse_prompt.txt # 时间解析提示词
│   ├── card_recommendation_prompt.txt # 卡片推荐提示词
│   ├── card_evaluation_prompt.txt   # 卡片评估提示词
│   ├── income_allocation_prompt.txt  # 收入分配提示词
│   ├── report_prompt.txt            # 通用报告提示词
│   └── rag_summarize.txt           # RAG总结提示词
│
├── config/                          # 配置文件
│   ├── prompts.yml                  # 提示词路径配置
│   ├── categories.yml               # 消费类别配置
│   ├── agent.yml                   # Agent配置
│   ├── budget.yml                  # 预算配置
│   ├── rag.yml                     # RAG配置
│   └── chroma.yml                  # 向量数据库配置
│
├── model/                           # 模型配置
│   ├── __init__.py
│   └── factory.py                   # 模型工厂（LLM配置）
│
├── rag/                             # RAG知识库
│   ├── __init__.py
│   ├── rag_service.py              # RAG服务
│   └── vector_store.py             # 向量存储
│
├── data/                            # 数据存储
│   ├── users/                       # 用户数据
│   │   └── {user_id}/
│   │       ├── transactions.json   # 消费记录
│   │       ├── budgets.json        # 预算配置
│   │       └── accounts.json       # 账户信息
│   ├── conversations/               # 对话历史
│   ├── knowledge/                  # 知识数据
│   │   └── cards/
│   ├── rewards/                    # 奖励数据
│   │   └── rewards_catalog.json    # 奖励目录
│   ├── points/                     # 积分数据
│   └── exports/                    # 导出数据
│
├── logs/                            # 日志文件
│   └── agent_YYYYMMDD.log          # 按日期的日志
│
├── chroma_db/                       # 向量数据库
│   └── chroma.sqlite3
│
├── __main__.py                      # 包入口
└── __init__.py                      # 包初始化
```

---

## 核心文件说明

### Agent系统 (agent/)

| 文件 | 功能 | 入口 |
|------|------|------|
| `react_agent.py` | 记账Agent，负责自然语言记账 | 智能记账页 |
| `finance_react_agent.py` | 财商分析Agent，负责消费分析 | 财商助手页 |
| `middleware.py` | 中间件：工具监控、prompt动态切换 | Agent内部 |

### 页面模块 (pages/)

| 文件 | 功能 | 导航名称 |
|------|------|----------|
| `_ai_finance_page.py` | 财商助手主页 | ai财商助手 |
| `_ledger_page.py` | 账本查看 | 我的账本 |
| `_budget_page.py` | 预算管理 | 预算设置 |
| `_accounts_page.py` | 账户管理 | 账户 |
| `_knowledge_cards_page.py` | 知识卡片 | 知识卡片 |
| `_points_mall_page.py` | 积分商城 | 积分商城 |
| `_settings_page.py` | 设置 | 设置 |

### 工具层 (utils/)

| 文件 | 功能 |
|------|------|
| `data_handler.py` | 消费数据CRUD、筛选、统计 |
| `evidence_pack_builder.py` | 构建分析用结构化证据包 |
| `card_state_manager.py` | 卡片激活、状态、评估管理 |
| `card_candidate_builder.py` | 程序层卡片候选预筛 |
| `card_repository.py` | 卡片数据存取 |
| `account_manager.py` | 储蓄/流动资金管理 |
| `income_manager.py` | 收入记录与分配 |
| `points_manager.py` | 积分获取与消耗 |
| `coupon_repository.py` | 优惠券查询与兑换 |
| `user_profile_manager.py` | 用户画像（阶段/偏好/语气） |
| `conversation_manager.py` | 对话历史存取 |
| `prompt_loader.py` | 提示词文件加载 |
| `model_error_helper.py` | 模型异常归一化处理 |

---

## 数据流图

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  app.py (页面路由)                                       │
└─────────────────────────────────────────────────────────┘
    │
    ├──────────────────────────────────────┐
    │                                      │
    ▼                                      ▼
┌─────────────┐                    ┌─────────────────┐
│ 记账Agent   │                    │ 财商分析Agent   │
│ react_agent │                    │ finance_react   │
└─────────────┘                    └─────────────────┘
    │                                      │
    ▼                                      ▼
┌─────────────┐                    ┌─────────────────┐
│ 工具调用    │                    │ 工具调用        │
│ - record_expense              │ - get_current_time
│ - get_categories              │ - build_evidence_pack
│ - rag_summarize               │ - rag_summarize
└─────────────┘                    │ - fill_context_for_report
    │                              └─────────────────┘
    ▼                                      │
┌─────────────┐                            ▼
│ data_handler │                    ┌─────────────────┐
│ (JSON存储)   │                    │ 中间件          │
└─────────────┘                    │ - monitor_tool  │
    │                              │ - report_prompt │
    ▼                              │   _switch       │
┌─────────────┐                    └─────────────────┘
│ JSON文件     │                            │
│ - transactions.json             ▼
│ - budgets.json                 ┌─────────────────┐
│ - accounts.json                │ evidence_pack   │
└─────────────┘                  │ _builder        │
                                  └─────────────────┘
```

---

## 文件命名规范

### Python文件
- 页面文件：`_`开头（Streamlit约定）
- 工具类：`_manager.py`、`_builder.py`、`_helper.py`、`_service.py`
- Agent文件：`_agent.py`

### 数据文件
- 用户数据：`{user_id}/transactions.json`
- 卡片状态：`{user_id}_card_state.json`
- 对话历史：`{user_id}_conversations.json`

### 文档文件
- 方案文档：`YYYY-MM-DD_名称_v版本.md`
- 完成说明：`YYYY-MM-DD_阶段_完成说明_v版本.md`
- 测试方案：`YYYY-MM-DD_功能_测试方案_v版本.md`

---

## 关键依赖关系

```
app.py
├── pages/_ai_finance_page.py
│   ├── agent/finance_react_agent.py
│   │   ├── agent/middleware.py
│   │   ├── agent/tools/agent_tools.py
│   │   │   └── utils/evidence_pack_builder.py
│   │   ├── utils/card_state_manager.py
│   │   └── utils/card_candidate_builder.py
│   └── utils/conversation_manager.py
│
├── pages/_ledger_page.py
│   └── utils/data_handler.py
│
├── pages/_accounts_page.py
│   ├── utils/account_manager.py
│   └── utils/income_manager.py
│
├── pages/_points_mall_page.py
│   ├── utils/points_manager.py
│   └── utils/coupon_repository.py
│
└── pages/_knowledge_cards_page.py
    └── utils/card_state_manager.py
```

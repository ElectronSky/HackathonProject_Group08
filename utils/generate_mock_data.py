
"""
模拟数据生成器 - 学生消费记录
为 usertest01 用户生成 2025-01-01 至 2026-03-20 的消费记录

数据特点：
- 符合中国大陆大学生消费水平（月均 1500-2500 元）
- 涵盖日常餐饮、购物、娱乐、学习等场景
- 不含具体品牌名，使用通用商户类型
- 适合产品功能测试和 Demo 展示
"""
import json
import random
from datetime import datetime, timedelta

# ==================== 配置参数 ====================
USER_ID = "usertest01"
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2026, 3, 20)
TARGET_TRANSACTIONS = 500  # 目标交易笔数

# ==================== 消费类别配置 ====================
# 权重表示该类目的消费频率，金额范围符合学生消费水平
CATEGORIES_CONFIG = {
    "餐饮": {
        "weight": 40,  # 占比 40%
        "subcategories": ["早餐", "午餐", "晚餐", "外卖", "奶茶", "咖啡", "零食", "聚餐", "夜宵"],
        "amount_ranges": {
            "早餐": (5, 15),
            "午餐": (12, 25),
            "晚餐": (12, 25),
            "外卖": (20, 40),
            "奶茶": (12, 25),
            "咖啡": (15, 35),
            "零食": (10, 50),
            "聚餐": (50, 150),
            "夜宵": (15, 50)
        },
        "descriptions": {
            "早餐": ["食堂早餐", "包子豆浆", "面包牛奶", "粥配小菜"],
            "午餐": ["食堂套餐", "两荤一素", "盖浇饭", "面条"],
            "晚餐": ["食堂晚餐", "简单小吃", "轻食沙拉"],
            "外卖": ["外卖快餐", "黄焖鸡", "麻辣烫", "炒饭"],
            "奶茶": ["珍珠奶茶", "水果茶", "芝士奶盖"],
            "咖啡": ["美式咖啡", "拿铁", "卡布奇诺"],
            "零食": ["薯片饼干", "坚果酸奶", "辣条"],
            "聚餐": ["同学聚餐", "火锅烤肉", "生日聚会"],
            "夜宵": ["烧烤串", "炸鸡啤酒", "泡面加餐"]
        }
    },
    "交通": {
        "weight": 8,
        "subcategories": ["公交", "地铁", "打车", "火车票", "飞机"],
        "amount_ranges": {
            "公交": (2, 5),
            "地铁": (3, 8),
            "打车": (15, 50),
            "火车票": (100, 300),
            "飞机": (500, 1500)
        },
        "descriptions": {
            "公交": ["公交车出行", "回学校公交"],
            "地铁": ["地铁通勤", "市区游玩"],
            "打车": ["紧急打车", "赶时间打车"],
            "火车票": ["寒假回家", "暑假返程", "周末短途"],
            "飞机": ["长途回家", "假期旅游"]
        }
    },
    "购物": {
        "weight": 15,
        "subcategories": ["日用品", "服装", "数码", "化妆品", "书籍"],
        "amount_ranges": {
            "日用品": (20, 100),
            "服装": (100, 500),
            "数码": (100, 800),
            "化妆品": (50, 300),
            "书籍": (30, 150)
        },
        "descriptions": {
            "日用品": ["洗发水沐浴露", "纸巾洗衣液", "宿舍用品"],
            "服装": ["冬季外套", "运动服", "休闲装", "鞋子"],
            "数码": ["蓝牙耳机", "手机壳", "充电宝", "U 盘"],
            "化妆品": ["护肤品", "面膜", "洗面奶"],
            "书籍": ["专业教材", "课外读物", "考试辅导书"]
        }
    },
    "娱乐": {
        "weight": 10,
        "subcategories": ["电影", "KTV", "游戏", "演出", "旅游"],
        "amount_ranges": {
            "电影": (30, 60),
            "KTV": (50, 100),
            "游戏": (30, 200),
            "演出": (100, 500),
            "旅游": (500, 2000)
        },
        "descriptions": {
            "电影": ["观看热映电影", "情侣观影"],
            "KTV": ["朋友聚会 KTV", "生日派对"],
            "游戏": ["游戏充值", "购买游戏", "会员订阅"],
            "演出": ["演唱会门票", "话剧表演"],
            "旅游": ["周边游", "长途旅行"]
        }
    },
    "学习": {
        "weight": 5,
        "subcategories": ["书籍", "课程", "文具", "考试"],
        "amount_ranges": {
            "书籍": (30, 150),
            "课程": (100, 500),
            "文具": (10, 50),
            "考试": (50, 200)
        },
        "descriptions": {
            "书籍": ["图书馆购书", "参考教材"],
            "课程": ["网课付费", "技能培训"],
            "文具": ["笔记本笔", "打印资料"],
            "考试": ["报名费", "资料费"]
        }
    },
    "医疗": {
        "weight": 3,
        "subcategories": ["药品", "门诊", "体检"],
        "amount_ranges": {
            "药品": (20, 100),
            "门诊": (100, 300),
            "体检": (200, 500)
        },
        "descriptions": {
            "药品": ["感冒药", "肠胃药", "创可贴"],
            "门诊": ["校医院看病", "牙科检查"],
            "体检": ["年度体检"]
        }
    },
    "社交": {
        "weight": 5,
        "subcategories": ["礼物", "聚会", "人情"],
        "amount_ranges": {
            "礼物": (50, 300),
            "聚会": (80, 200),
            "人情": (100, 500)
        },
        "descriptions": {
            "礼物": ["同学生日礼物", "教师节礼物"],
            "聚会": ["班级聚餐", "社团活动"],
            "人情": ["婚礼份子钱", "满月礼"]
        }
    },
    "生活缴费": {
        "weight": 4,
        "subcategories": ["话费", "网费", "水电费"],
        "amount_ranges": {
            "话费": (30, 100),
            "网费": (30, 60),
            "水电费": (20, 100)
        },
        "descriptions": {
            "话费": ["每月话费充值", "流量包"],
            "网费": ["宿舍宽带费"],
            "水电费": ["宿舍电费", "水费"]
        }
    },
    "运动": {
        "weight": 2,
        "subcategories": ["健身", "体育用品", "门票"],
        "amount_ranges": {
            "健身": (0, 200),
            "体育用品": (50, 300),
            "门票": (30, 100)
        },
        "descriptions": {
            "健身": ["操场跑步", "健身房办卡"],
            "体育用品": ["篮球足球", "运动鞋服"],
            "门票": ["体育馆门票"]
        }
    },
    "其他": {
        "weight": 8,
        "subcategories": ["临时支出", "意外支出", "杂项"],
        "amount_ranges": {
            "临时支出": (10, 200),
            "意外支出": (50, 500),
            "杂项": (5, 100)
        },
        "descriptions": {
            "临时支出": ["急需用品", "临时购物"],
            "意外支出": ["物品损坏赔偿", "罚款"],
            "杂项": ["零碎支出", "找不到分类的"]
        }
    }
}


def generate_transaction_id(date, index):
    """生成唯一交易 ID"""
    return f"txn_{date.strftime('%Y%m%d')}_{index:03d}"


def generate_amount(subcategory, config):
    """
    根据子类别生成合理的消费金额
    
    Args:
        subcategory: 子类别名称
        config: 该类别的配置信息
    
    Returns:
        float: 消费金额
    """
    min_amt, max_amt = config["amount_ranges"].get(subcategory, (10, 100))
    
    # 在范围内随机生成
    amount = random.uniform(min_amt, max_amt)
    
    # 让金额看起来更真实（以 .8/.9 结尾的概率较高）
    if random.random() < 0.7:
        amount = round(int(amount) + random.choice([0.5, 0.8, 0.9]), 2)
    else:
        amount = round(amount, 2)
    
    return amount


def generate_description(category, subcategory):
    """生成消费描述"""
    descriptions = CATEGORIES_CONFIG[category]["descriptions"].get(
        subcategory, 
        [f"{subcategory}消费"]
    )
    return random.choice(descriptions)


def generate_transactions():
    """
    生成所有交易记录
    
    Returns:
        list: 交易记录列表
    """
    transactions = []
    current_date = START_DATE
    transaction_index = 1
    
    # 计算总天数
    total_days = (END_DATE - START_DATE).days + 1
    
    # 按权重分配每天的平均消费次数
    avg_transactions_per_day = TARGET_TRANSACTIONS / total_days
    
    while current_date <= END_DATE:
        # 判断今天是否有消费（周末/节假日消费概率更高）
        is_weekend = current_date.weekday() >= 5  # 周六周日
        is_holiday = current_date.month in [1, 2, 7, 8]  # 寒暑假
        
        # 基础消费概率 + 周末/节假日加成
        base_prob = min(avg_transactions_per_day / 3, 0.8)
        if is_weekend:
            base_prob *= 1.5
        if is_holiday:
            base_prob *= 1.3
        
        # 今天生成的消费笔数
        if random.random() < base_prob:
            num_transactions = random.randint(1, int(avg_transactions_per_day * 2) + 1)
            
            for i in range(num_transactions):
                # 按权重随机选择类别
                categories = list(CATEGORIES_CONFIG.keys())
                weights = [CATEGORIES_CONFIG[c]["weight"] for c in categories]
                category = random.choices(categories, weights=weights)[0]
                
                # 随机选择子类别
                subcategory = random.choice(CATEGORIES_CONFIG[category]["subcategories"])
                
                # 生成金额
                amount = generate_amount(subcategory, CATEGORIES_CONFIG[category])
                
                # 特殊处理：某些日期可能有收入（红包、兼职等）
                if random.random() < 0.01:  # 1% 概率有收入
                    amount = -random.uniform(200, 1000)
                    category = "其他收入"
                    subcategory = "兼职/红包"
                    description = random.choice(["兼职收入", "春节红包", "奖学金"])
                else:
                    description = generate_description(category, subcategory)
                
                # 生成交易时间（合理的时段）
                if subcategory == "早餐":
                    hour = random.randint(7, 9)
                elif subcategory in ["午餐", "外卖"]:
                    hour = random.randint(11, 13)
                elif subcategory == "晚餐":
                    hour = random.randint(17, 19)
                elif subcategory == "夜宵":
                    hour = random.randint(21, 23)
                else:
                    hour = random.randint(9, 22)
                
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                
                created_time = current_date.replace(hour=hour, minute=minute, second=second)
                
                transaction = {
                    "transaction_id": generate_transaction_id(current_date, transaction_index),
                    "date": current_date.strftime("%Y-%m-%d"),
                    "category": category,
                    "subcategory": subcategory,
                    "amount": round(abs(amount), 2),
                    "description": description,
                    "created_at": created_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "updated_at": created_time.strftime("%Y-%m-%dT%H:%M:%S")
                }
                
                transactions.append(transaction)
                transaction_index += 1
        
        current_date += timedelta(days=1)
    
    # 添加一些特殊的固定消费（如每月的话费、固定的培训班费用等）
    for month in range(1, 13):  # 修正：1-12 月（原代码错误地写了 14）
        month_date = datetime(2025, month, 15)
        if month_date <= END_DATE:
            # 每月话费
            transactions.append({
                "transaction_id": generate_transaction_id(month_date, 900 + month),
                "date": month_date.strftime("%Y-%m-%d"),
                "category": "生活缴费",
                "subcategory": "话费",
                "amount": 50.00,
                "description": "每月话费充值",
                "created_at": month_date.strftime("%Y-%m-%dT10:00:00"),
                "updated_at": month_date.strftime("%Y-%m-%dT10:00:00")
            })
    
    # 添加 2026 年的话费
    for month in range(1, 4):  # 2026 年 1-3 月
        month_date = datetime(2026, month, 15)
        if month_date <= END_DATE:
            transactions.append({
                "transaction_id": generate_transaction_id(month_date, 900 + 12 + month),
                "date": month_date.strftime("%Y-%m-%d"),
                "category": "生活缴费",
                "subcategory": "话费",
                "amount": 50.00,
                "description": "每月话费充值",
                "created_at": month_date.strftime("%Y-%m-%dT10:00:00"),
                "updated_at": month_date.strftime("%Y-%m-%dT10:00:00")
            })
    
    # 添加一些学期初的固定支出
    semester_starts = [
        datetime(2025, 3, 1),   # 2025 春季学期
        datetime(2025, 9, 1),   # 2025 秋季学期
        datetime(2026, 3, 1)    # 2026 春季学期
    ]
    
    for semester_start in semester_starts:
        if semester_start <= END_DATE:
            # 开学买文具
            transactions.append({
                "transaction_id": generate_transaction_id(semester_start, 950),
                "date": semester_start.strftime("%Y-%m-%d"),
                "category": "学习",
                "subcategory": "文具",
                "amount": 85.00,
                "description": "开学购买文具用品",
                "created_at": semester_start.strftime("%Y-%m-%dT14:00:00"),
                "updated_at": semester_start.strftime("%Y-%m-%dT14:00:00")
            })
    
    # 按日期排序
    transactions.sort(key=lambda x: x["date"])
    
    return transactions


def main():
    """主函数：生成并保存模拟数据"""
    print("=" * 60)
    print("开始生成学生消费模拟数据...")
    print("=" * 60)
    
    # 生成交易记录
    transactions = generate_transactions()
    print(f"✓ 生成了 {len(transactions)} 条交易记录")
    
    # 构建完整的数据结构
    data = {
        "user_id": USER_ID,
        "created_at": START_DATE.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated_at": END_DATE.strftime("%Y-%m-%dT%H:%M:%S"),
        "transactions": transactions
    }
    
    # 保存到文件
    output_file = f"data/user_data/{USER_ID}.json"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 数据已保存到：{output_file}")
    except Exception as e:
        print(f"✗ 保存失败：{e}")
        return
    
    # 打印统计信息
    total_amount = sum(t["amount"] for t in transactions if t["amount"] > 0)
    income_amount = abs(sum(t["amount"] for t in transactions if t["amount"] < 0))
    
    print("\n" + "=" * 60)
    print("数据统计摘要")
    print("=" * 60)
    print(f"📊 总交易笔数：{len(transactions)}")
    print(f"💰 总支出金额：¥{total_amount:.2f}")
    print(f"💵 总收入金额：¥{income_amount:.2f}")
    print(f"📈 净支出：¥{total_amount - income_amount:.2f}")
    print(f"📅 时间跨度：{START_DATE.strftime('%Y-%m-%d')} 至 {END_DATE.strftime('%Y-%m-%d')}")
    print(f"📆 平均每月支出：¥{total_amount/14:.2f}")
    
    # 按类别统计
    category_stats = {}
    for t in transactions:
        if t["amount"] > 0:
            cat = t["category"]
            category_stats[cat] = category_stats.get(cat, 0) + t["amount"]
    
    print("\n" + "=" * 60)
    print("各类别支出统计（TOP 5）")
    print("=" * 60)
    sorted_cats = sorted(category_stats.items(), key=lambda x: x[1], reverse=True)
    for idx, (cat, amount) in enumerate(sorted_cats[:5], 1):
        percentage = (amount / total_amount * 100) if total_amount > 0 else 0
        print(f"{idx}. {cat}: ¥{amount:.2f} ({percentage:.1f}%)")
    
    print("\n" + "=" * 60)
    print("生成完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

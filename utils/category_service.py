
"""
消费类别标准化服务
确保分类一致性，避免 AI 生成不规范的类别名称
"""

#对于调用的self.load_categories统一改为self.standard_categories



#python -m utils.category_service 使用if name == main


from utils.path_tools import get_abs_path
from utils.config_handler import categories_conf

#classifier
class CategoryService:
    """
       消费类别管理类

       核心功能：
       - 加载标准类别配置
       - 验证类别有效性
       - 智能推荐类别
    """

    def __init__(self):
        """初始化并加载类别配置"""
        self.config_path = get_abs_path("config/categories.yml")
        self.standard_categories = categories_conf["standard_categories"]

    def get_all_categories(self) -> list:
        """
        获取所有标准类别及其子类名称

        Returns:
            list: 包含类别信息的字典列表
                  格式：[{"category": "类别名", "sub_categories": {子类集合}}, ...]
        """
        category_list = []
        
        for category_item in self.standard_categories:
            category_data = {
                "category": category_item["category"],
                "sub_categories": set(category_item.get("subcategories", []))
            }
            category_list.append(category_data)
        
        return category_list

    def get_standard_category_names(self) -> list:
        """
        获取配置文件中的所有标准一级类别名称

        Returns:
            list: 标准类别名称列表
        """
        return [
            category_item["category"].strip()
            for category_item in self.standard_categories
            if category_item.get("category")
        ]

    def get_merged_category_names(self, extra_categories: list = None) -> list:
        """
        获取去重后的类别名称列表。

        去重规则：
        1. 先保留配置文件中的标准类别顺序；
        2. 再追加用户交易里出现、但标准配置中没有的新类别；
        3. 按类别名称字符串去首尾空格后去重。

        Args:
            extra_categories: 额外类别列表（通常来自用户历史交易）

        Returns:
            list: 合并并去重后的类别名称列表
        """
        merged_categories = []
        seen = set()

        # 先按配置文件中的标准顺序加入，保证页面展示顺序稳定
        for category_name in self.get_standard_category_names():
            normalized_name = category_name.strip()
            if normalized_name and normalized_name not in seen:
                merged_categories.append(normalized_name)
                seen.add(normalized_name)

        # 再追加用户数据里独有的类别，避免遗漏历史上已经存在的数据类别
        for category_name in extra_categories or []:
            normalized_name = str(category_name).strip()
            if normalized_name and normalized_name not in seen:
                merged_categories.append(normalized_name)
                seen.add(normalized_name)

        return merged_categories

    def get_subcategories(self, category_name: str) -> list:
        """
        获取某类别的所有子类别

        Args:
            category_name: 一级类别名称

        Returns:
            list: 子类别列表，不存在返回空列表
        """
        for cat in self.standard_categories:
            if cat['category'] == category_name:
                return cat.get('subcategories', [])
        return []

    def validate_category(self, category: str) -> bool:
        """
        验证类别是否为标准类别

        Args:
            category: 待验证的类别名称

        Returns:
            bool: 是否为有效类别
        """
        return category in [cat['category'] for cat in self.standard_categories]


if __name__ == "__main__":
    service = CategoryService()
    print(service.get_all_categories())
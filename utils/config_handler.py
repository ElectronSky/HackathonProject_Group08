
#配置文件中枢

import yaml
# 支持相对导入和直接运行两种方式
try:
    from .path_tools import get_abs_path
except ImportError:
    from path_tools import get_abs_path


#导出config的快递员类型
class ConfigHandler(object):

    #传入config_path，默认为一段带有预设名称的绝对路径encoding="utf-8"
    #然后按照这个路径打开的时候用yaml.load()并返回文件内对应内容
    @staticmethod
    def load_rag_config(config_path: str=get_abs_path("config/rag.yml"), encoding="utf-8"):
        with open(config_path, "r", encoding=encoding) as f:
            #yaml.load()快速读取想要的value
            return yaml.load(f.read(), Loader=yaml.FullLoader)

    @staticmethod
    def load_chroma_config(config_path: str=get_abs_path("config/chroma.yml"), encoding="utf-8"):
        with open(config_path, "r", encoding=encoding) as f:
            return yaml.load(f.read(), Loader=yaml.FullLoader)

    @staticmethod
    def load_prompts_config(config_path: str=get_abs_path("config/prompts.yml"), encoding="utf-8"):
        with open(config_path, "r", encoding=encoding) as f:
            return yaml.load(f.read(), Loader=yaml.FullLoader)

    @staticmethod
    def load_agent_config(config_path: str = get_abs_path("config/agent.yml"), encoding="utf-8"):
        with open(config_path, "r", encoding=encoding) as f:
            return yaml.load(f.read(), Loader=yaml.FullLoader)

    @staticmethod
    def load_categories_config(config_path: str = get_abs_path("config/categories.yml"), encoding="utf-8"):
        with open(config_path, "r", encoding=encoding) as f:
            return yaml.load(f.read(), Loader=yaml.FullLoader)

    @staticmethod
    def load_budget_config(config_path: str = get_abs_path("config/budget.yml"), encoding="utf-8"):
        with open(config_path, "r", encoding=encoding) as f:
            return yaml.load(f.read(), Loader=yaml.FullLoader)


#对应的配置的值通过类ConfigHandler的.load_xxx_config()方法获取,读取的是config里面的四个文件里的配置值
#形成了四个字典!
rag_conf = ConfigHandler.load_rag_config()
chroma_conf = ConfigHandler.load_chroma_config()
prompts_conf = ConfigHandler.load_prompts_config()
agent_conf = ConfigHandler.load_agent_config()
categories_conf = ConfigHandler.load_categories_config()
budget_conf = ConfigHandler.load_budget_config()

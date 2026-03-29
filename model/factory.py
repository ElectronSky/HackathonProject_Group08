
#模型工厂 - 打包提供模型的功能

from abc import ABC
from abc import abstractmethod

from langchain_community.chat_models.tongyi import ChatTongyi, BaseChatModel
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.embeddings import Embeddings

from typing import Optional

try:
    from ..utils.config_handler import rag_conf
    from ..utils.logger_handler import logger
except ImportError:
    from utils.config_handler import rag_conf
    from utils.logger_handler import logger

#基础抽象类 继承于python内置的抽象类

class BaseModelFactory(ABC):
    #定义抽象方法 - 生成器 -返回类型值：嵌入模型 或者 聊天模型
    #抽象方法 - 抽象方法不能有方法体，只能声明方法名，方法名后面加冒号，方法体写在子类中
    #声明这个方法返回值类型为Embeddings或者BaseChatModel
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        pass

#提供子类实现

#聊天模型类型ChatModelFactory 继承于 BaseModelFactory 抽象父类
#必须写入父类具有的generator方法
class ChatModelFactory(BaseModelFactory):
    @staticmethod
    def _normalize_chat_model_name(model_name: str) -> str:
        """
        兼容项目内常见的通义模型别名写法。

        说明：
        - 当前 langchain_community 的 `ChatTongyi` 在这个项目环境下，
          对 `qwen3.5-plus` 这类名称会触发 `InvalidParameter / url error`；
        - 但经实测，`qwen-plus` 是可正常调用的；
        - 因此这里做一层最小别名归一化，避免配置里写了“口语化/产品化名称”时直接把调用打崩。
        """
        alias_map = {
            "qwen3.5-plus": "qwen-plus",
            "qwen-3.5-plus": "qwen-plus",
            "qwen3.5-max": "qwen-max",
            "qwen-3.5-max": "qwen-max",
            "qwen3.5-turbo": "qwen-turbo",
            "qwen-3.5-turbo": "qwen-turbo",
        }

        normalized_name = alias_map.get(model_name, model_name)
        if normalized_name != model_name:
            logger.warning(
                f"[ChatModelFactory]检测到模型别名 {model_name}，已自动归一化为 {normalized_name} 以兼容当前 ChatTongyi 调用。"
            )

        return normalized_name

    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        #返回一个聊天模型对象，模型在配置文件里设定，这里直接进行调用
        normalized_model_name = self._normalize_chat_model_name(rag_conf["chat_model_name"])
        logger.info(f"[ChatModelFactory]当前聊天模型配置：{rag_conf['chat_model_name']}，实际调用模型：{normalized_model_name}")
        return ChatTongyi(model=normalized_model_name)

class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return DashScopeEmbeddings(model=rag_conf["embedding_model_name"])

#在这里创建两个对象，创建的同时分别调用两个工厂类，生成对应的模型对象，存入在两个变量里，要用的时候就可以直接取用这两个变量
chat_model = ChatModelFactory().generator()
embed_model = EmbeddingsFactory().generator()
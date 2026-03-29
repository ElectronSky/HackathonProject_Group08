from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

from .vector_store import VectorStoreService
try:
    from ..model.factory import chat_model
    from ..utils.prompt_loader import load_rag_prompts
except ImportError:
    from importlib import import_module

    chat_model = import_module("model.factory").chat_model
    load_rag_prompts = import_module("utils.prompt_loader").load_rag_prompts


import html



def print_prompt(prompt):
    """打印提示词，自动换行长文本，处理各种编码"""
    print("=" * 50)
    print("RAG 提示词内容：")
    print("=" * 50)

    # 1. 先转为字符串（处理 LangChain 的 PromptValue 对象）
    prompt_str = str(prompt)

    # 2. 解码 HTML 实体（如果有的话，如 &#x000A; → 换行）
    decoded = html.unescape(prompt_str)

    # 3. 清理其他可能的特殊字符表示
    # 将字面量的 \n 替换为实际换行符（如果字符串中包含两个字符 \ 和 n）
    if r'\n' in decoded:
        decoded = decoded.replace(r'\n', '\n')

    # 4. 直接打印，让 \n 自然换行
    print(decoded)

    print("=" * 50)
    return prompt

#综合所有rag服务的rag中枢
class RagSummarizeService(object):


    def __init__(self):
        #向量存储
        self.vector_store = VectorStoreService()
        #检索器
        self.retriever = self.vector_store.get_retriever()
        #提示词
        self.prompt_text = load_rag_prompts()
        #加载提示词
        #PromptTemplate.from_template() 创建一个提示词对象并传入对应提示词生成提示词模板
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        #模型
        self.model = chat_model
        #加载一个链出来
        self.chain = self._init_chain()


    #简单的链(无历史记录),导入提示词模板传入模型获取输出结果str
    def _init_chain(self):
        chain = self.prompt_template | RunnableLambda(print_prompt) | self.model | StrOutputParser()
        return chain

    #输入用户输入,获取检索结果
    def retriever_docs(self, query):
        return self.retriever.invoke(query)

    def rag_summarize(self, query):

        #含有key - input - 用户输入 / key - context - 参考资料
        input_dict = {}

        #参考资料文档list
        context_docs = self.retriever_docs(query)

        # 如果当前没有检索到任何资料，就直接返回空字符串，避免模型在无依据时自行发挥
        if not context_docs:
            return ""

        context = ""

        t=0
        for doc in context_docs:
            t+=1
            context += f"参考资料{t}: {doc.page_content} | 参考元数据: {doc.metadata}"

        input_dict["input"] =  query
        input_dict["context"] = context

        #self.chain 调用._init_chain()返回一个基础链, .invoke()调用这个链传入input_dict
        return self.chain.invoke(input_dict)


if __name__ == '__main__':

    rag = RagSummarizeService()
    print(rag.rag_summarize("小户型适合哪些扫地机器人"))


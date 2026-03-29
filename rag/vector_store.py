
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from utils.config_handler import chroma_conf
from utils.file_handler import get_file_md5_hex, listdir_with_allowed_type, pdf_loader, txt_loader
from utils.logger_handler import logger
from utils.path_tools import get_abs_path

from model.factory import embed_model






#RAG的向量存储相关功能
class VectorStoreService:
    def __init__(self):

        #chroma向量存储
        #self.vector_store 在存储chroma对象时自带.add_documents()方法，传入documents类型对象可以存储
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=get_abs_path(chroma_conf["persist_directory"]),
        )

        #文本分割器
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )

    def get_retriever(self):
        #as_retriever 建立一个检索器对象并传入配置的变量中的检索个数上限
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})

    def input_document(self):
        # 从数据文件夹里读取切割数据文件，转为向量存入向量库
        # 计算md5做去重

        def check_md5_hex(md5_hex: str):
            if not os.path.exists(get_abs_path(chroma_conf["md5_hex_store"])):
                open(get_abs_path(chroma_conf["md5_hex_store"]), "w", encoding="utf-8").close()
                return False
            else:
                #open(file...).readlines()
                for line in open(get_abs_path(chroma_conf["md5_hex_store"]), "r", encoding="utf-8").readlines():
                    line = line.strip()

                    if line == md5_hex:
                        #true值表示已处理过
                        return True

                return False

        def save_md5_hex(md5_hex: str):
            with open(get_abs_path(chroma_conf["md5_hex_store"]), "a", encoding="utf-8") as f:
                f.write(md5_hex + "\n")

        #获取对应路径的文件转为list[Document]
        def get_file_documents(file_path: str):
            if file_path.endswith("txt"):
                return txt_loader(file_path)

            if file_path.endswith("pdf"):
                return pdf_loader(file_path)

            #如果不是这两种文件那就返回空文档
            return []

        #得到data文件夹里的符合条件的文件列表
        allowed_file_path: list[str] = listdir_with_allowed_type(
            ####修改vector_store.py，在调用时转换为绝对路径：
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"])
        )

        #对于每一个符合条件的 文件
        for file_path in allowed_file_path:
            #获取文件的md5
            md5_hex = get_file_md5_hex(file_path)
            #判断是否已处理过
            if check_md5_hex(md5_hex):
                logger.info(f"{file_path} 已处理过")
                continue

            #未处理过文件的md5说明这是个新文件，存起来
            try:
                #获取文件转为Document对象
                documents = get_file_documents(file_path)

                if not documents:
                    logger.info(f"{file_path} 无内容")
                    continue

                #将新的decuments形式文件切割(转为documents就是要为了给切割器传入documents对象进行文本切割
                splited_documents = self.spliter.split_documents(documents)

                if not splited_documents:
                    logger.info(f"{file_path} 分片后无内容")
                    continue

                #将切割后的documents存进向量库
                self.vector_store.add_documents(splited_documents)

                #记录已经存入的文件的md5值，防止重复加载
                save_md5_hex(md5_hex)
                logger.info(f"{file_path} 已处理")

            except Exception as e:
                #打印错误信息,exc_info=True打印错误信息
                logger.error(f"存储并切片文件进入chroma并记录md5过程中文件 {file_path} 出错：{str(e)}", exc_info=True)

if __name__ == '__main__':
    # 创建一个向量存储服务对象
    vs = VectorStoreService()

    #这条代码自动读取配置里面写好的文件位置里面对应的文件，并把文件内容存进向量库，并记录md5
    vs.input_document()

    #获取向量存储服务对象的一个检索器对象，检索上限在配置里写好了
    retriever = vs.get_retriever()

    res = retriever.invoke("迷路")
    #对于检索到的每一块相似度高的文档
    for r in res:
        print("*"*20, r.page_content, "*"*20)


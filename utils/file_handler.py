
#一些文件操作的方法中枢，方便切分项目内容，与导包调用。

# 负责获取文件的md5十六进制字符串
# 返回文件夹的内部文件名列表
# 还有pdf / txt加载器

#MD5
import hashlib

#文件操作
import os

#日志logging的依赖类
from typing import Optional

# 支持相对导入和直接运行两种方式
try:
    from .logger_handler import logger
except ImportError:
    from logger_handler import logger

#加载器
from langchain_core.documents import Document
from langchain_community.document_loaders import CSVLoader, PyPDFLoader, TextLoader


def get_file_md5_hex(filepath: str) -> Optional[str]:
    """
    计算文件的MD5哈希值，返回十六进制字符串
    :param filepath: 文件的绝对/相对路径
    :return: 成功返回32位MD5十六进制字符串，失败返回None
    """

    # 1. 校验文件是否存在
    if not os.path.exists(filepath):
        print(f"文件不存在: {filepath}")
        return None

    # 2. 校验是否是文件（避免传入文件夹路径）
    if not os.path.isfile(filepath):
        print(f"错误：{filepath} 不是有效文件")
        return None

    # 3. 初始化MD5对象
    md5_obj = hashlib.md5()

    # 4. 分片读取大文件（避免一次性加载占满内存）
    chunk_size = 4096  # 4KB分片，可根据需求调整
    try:
        with open(filepath, "rb") as f:
            while True:
                # f.read(chunk_size) 按顺序读取读取指定大小的未读数据
                chunk = f.read(chunk_size)
                # 已经读完了
                if not chunk:
                    break
                # 没读完就把chunk更新-加进md5_obj
                md5_obj.update(chunk)

            # 返回MD5十六进制字符串
            return md5_obj.hexdigest()

    except Exception as e:

        # 打印错误信息, 用日志的方式存储（长期性） 不在控制台输出（临时性）
        logger.error(f"计算文件MD5出错：{e}")
        return None

# 获取指定路径下的所有符合类型要求的文件 path是一个相对路径，要查询这个目录下的文件名
def listdir_with_allowed_type(path: str, allowed_types: tuple[str]):
    files = []

    #os.path.isdir()这个函数用来判断一个路径是否是一个目录,需要绝对路径才能正确判断
    if not os.path.isdir(path):
        logger.error(f"{path} 不是一个有效的目录")
        # 返回空列表
        return []

    for file in os.listdir(path):
        # os.listdir(path)返回path下的所有文件仅名为一个列表
        # 拼接拎出来的每一个文件的绝对路径
        file_path = os.path.join(path, file)
        # 判断文件类型
        # 如果文件类型符合要求就添加到列表中
        if file.endswith(allowed_types):
            files.append(file_path)

    # 用tuple返回list，不允许改变
    return tuple(files)

def pdf_loader(file_path: str, passwd =  None) -> list[Document]:
    """
    加载PDF文件
    :param file_path: 文件的绝对/相对路径
    :return: 列表，每个元素是一个Document对象
    """

    # 创建PDF加载器
    loader = PyPDFLoader(file_path, passwd)
    # 通过.load()方法加载
    return loader.load()

def txt_loader(file_path: str) -> list[Document]:
    """
    加载txt文件
    :param file_path: 文件的绝对/相对路径
    :return: 列表，每个元素是一个Document对象
    """

    # 创建txt加载器
    loader = TextLoader(file_path, encoding="utf-8")
    # 通过.load()方法加载
    return loader.load()











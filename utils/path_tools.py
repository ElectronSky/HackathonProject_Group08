
#路径中枢

#为整个工程提供统一的绝对路径
#相对路径不安全
#对输入的相对路径，返回当前绝对路径


import os
def get_project_root():
    #__file__代表当前文件所在的目录
    #os.path.abspath(xx)获取xx的绝对路径
    #os.path.dirname(xx)获取xx的父目录/上一级目录
    #当前文件绝对路径
    current_file_path = os.path.abspath(__file__)
    #当前文件夹绝对路径os.path.dirname()获取传入文件的绝对路径
    current_folder_path = os.path.dirname(current_file_path)
    #获取当前工程根目录
    project_root = os.path.dirname(current_folder_path)

    return project_root


def get_abs_path(relative_path):

    project_root = get_project_root()
    return os.path.join(project_root, relative_path)



if __name__ == '__main__':
    print(get_abs_path(r"config\config.txt"))
    print(get_project_root())
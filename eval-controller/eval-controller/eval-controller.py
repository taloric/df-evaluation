import sys
import multiprocessing

from eval_lib.common.logger import LoggerManager
from manager.manager import Manager
from server.server import ServerProcess
from common.mysql import init_mysql
from config import conf

# 主程序入口
if __name__ == '__main__':
    # 检查配置文件的有效性
    if not conf.is_valid():
        print('Invalid conf value, error exit.')
        sys.exit(1)
    # 初始化日志管理器，设置日志文件路径
    LoggerManager(log_file=f"{conf.log_dir}/evaluation.log")

    # 初始化MySQL连接
    init_mysql()

    # 使用多进程管理器创建一个消息队列
    # httpServer写入消息，manager读取消息
    m = multiprocessing.Manager()
    message_queue = m.Queue()

    # 初始化并启动runner管理进程
    manager = Manager(message_queue)
    manager.start()

    # 初始化并启动服务进程
    server = ServerProcess(queue=message_queue)
    server.start()
    # 等待服务进程执行完毕
    server.join()

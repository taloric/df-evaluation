import subprocess
import os
import traceback

from eval_lib.common import logger
from eval_lib.common.exceptions import InternalServerErrorException
from common.model import ResultPostLog, ResultGetLog, ResultLogResponse, ResultGetFile, ResultFileResponse
from config import conf

log = logger.get_logger()
POST_TIMEOUT = 10


class ResultWorker(object):

    def post_log(self, msg: ResultPostLog):
        """
        将日志消息写入到文件中。
    
        参数:
        - msg: ResultPostLog 类型。
    
        返回值:
        - 无
        """
        # 根据消息的uuid生成日志文件路径
        log_file = f"{conf.runner_data_dir}/tmp/runner-{msg.uuid}.log"
        # log.info(f"get post log msg {msg.uuid}, logfile: {log_file}")

        # 如果消息数据为空，则不进行任何操作
        if not msg.data:
            return
        try:
            # 将日志数据追加写入到文件中
            with open(log_file, 'a+') as file:
                file.write(msg.data)
        except Exception as e:
            # 记录日志写入过程中的错误，并抛出异常
            log.error(f"post log error {e}")
            raise e

    def get_log(self, msg: ResultGetLog = None) -> dict:
        """
        获取指定运行器日志的一部分内容。
        
        参数:
        - msg: ResultGetLog 类型，包含需要获取日志的 UUID 和索引信息。
        
        返回值:
        - 一个字典，包含日志响应的内容，UUID、日志条目、行数。
        """
        # 构造日志文件路径
        log_file = f"{conf.runner_data_dir}/tmp/runner-{msg.uuid}.log"
        if not os.path.exists(log_file):
            log_file = f"{conf.runner_data_dir}/runner-{msg.uuid}/log/runner.log"
        log.info(f"get log msg {msg}, logfile: {log_file}")

        # 初始化日志响应对象
        rlr = ResultLogResponse(uuid=msg.uuid, logs=[])
        if not os.path.exists(log_file):
            return rlr
        try:
            # 处理行大小设置，为0时则获取全部
            line_size = "$" if msg.line_size < 1 else msg.line_size
            # 使用sed命令获取指定行范围的日志内容
            sed_cmd = f"sed -n '{msg.line_index},{line_size}p' {log_file}"
            p = subprocess.run(
                sed_cmd, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logs = p.stdout.decode('utf-8')
            err = p.stderr.decode('utf-8')
            if err:
                raise InternalServerErrorException(err)

            # 使用wc命令计算日志文件的行数
            wc_cmd = f"wc -l {log_file}"
            p = subprocess.run(
                wc_cmd, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            wc = p.stdout.decode('utf-8')
            err = p.stderr.decode('utf-8')
            if err:
                raise InternalServerErrorException(err)

            # 如果有日志内容，则处理并设置到rlr对象中
            if logs:
                logs = logs.split("\n")[:-1]
                rlr.line_size = len(logs)
                rlr.logs = logs
                rlr.line_index = msg.line_index
                # 设置日志总行数
                if wc:
                    rlr.line_count = int(wc.split(" ")[0])
        except Exception as e:
            log.error(traceback.format_exc())
            log.error(f"get log error {e}")
            raise e

        # 将rlr对象转换为JSON格式返回
        return rlr.to_json()

    def get_performance_results(self):
        # TODO: luyao 获取性能测试结果
        pass

    def get_performance_md(self, info: ResultGetFile):
        prefix = f"runner-{info.uuid}"
        md_dir = f"{conf.runner_data_dir}/{prefix}/report"
        data = []
        if not os.path.exists(md_dir):
            return []
        for filename in os.listdir(md_dir):
            if not filename.endswith(".md"):
                continue
            file_path = os.path.join(md_dir, filename)
            if os.path.isfile(file_path):
                with open(file_path, "r") as f:
                    data.append([filename, f.read()])
        return data

    def post_zip(self, filename, zipfile):
        try:
            prefix = filename.split(".zip")[0]
            zipfile.extractall(path=f"{conf.runner_data_dir}/")
            files = os.listdir(f"{conf.runner_data_dir}/{prefix}")
            log.info(files)
        except Exception as e:
            log.error(f"post zip error {e}")
            raise e

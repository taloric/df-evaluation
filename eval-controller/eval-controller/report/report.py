import os
import glob
import importlib
from eval_lib.common import logger

log = logger.get_logger()


class ReportManager(object):

    def __init__(self, report_path=None, report_engines=None):
        self.engines = {}
        self.report_path = report_path
        self.report_engines = report_engines

    def get_report_engine(self):
        plugin_files = glob.glob(os.path.join(f"./report", "*.py"))
        log.info(f"plugin_files: {plugin_files}")
        for file in plugin_files:
            # 获取文件名（不含后缀）
            file_name = os.path.basename(file)[:-3]
            # 使用importlib.import_module动态导入模块
            module = importlib.import_module(
                f"report.{file_name}", package="report"
            )
            # 遍历模块中定义的所有属性和方法
            for name in dir(module):
                # 如果属性或方法是以Plugin开头的类，则导入该类
                if name.startswith("Report") and name != "ReportBase" and name != "ReportManager":
                    if self.report_engines:
                        if name not in self.report_engines:
                            continue
                    cls = getattr(module, name)
                    # 将类添加到当前模块的全局变量中
                    self.engines[name] = cls

    def run(self):
        self.get_report_engine()
        for name, engine in self.engines.items():
            log.info(f"report {name} start!")
            engine(data_path=self.report_path).run()
            log.info(f"report {name} end!")

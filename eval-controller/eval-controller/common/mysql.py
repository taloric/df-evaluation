import time
from . import const
from eval_lib.databases.mysql.db import db
from eval_lib.common.logger import get_logger
from eval_lib.databases.mysql.models.models import CaseRecord, CaseReport, Component

log = get_logger()


def init_mysql():
    """
    初始化MySQL数据库。

    """
    start_time = time.time()
    while True:
        try:
            db.connect()
            db.create_tables([CaseRecord, CaseReport, Component])
            break  # 如果成功连接并创建表，则退出循环
        except Exception as e:
            if time.time() - start_time > const.WAIT_MYSQL_RUNNING_TIMEOUT:
                log.error("MySQL deployment timed out")
                raise TimeoutError("MySQL deployment timed out")
            log.error(f"init mysql failed: {e}")
            time.sleep(20)  # 等待 20 秒后重试连接


def update_case_record(uuid: str, **kwargs):
    """
    更新特定测试记录的信息。

    参数:
    - uuid: str，要更新的案例记录的唯一标识符。
    - **kwargs: 额外的关键字参数，代表要更新的字段及其新值。
    """
    try:
        # 根据UUID更新案例记录中的信息
        CaseRecord.update(**kwargs).where(CaseRecord.uuid == uuid).execute()
        log.info(f"update case record {uuid} success")
    except Exception as e:
        # 记录更新失败的日志并抛出异常
        log.error(f"update case record: {uuid} , {kwargs}, failed: {e}")
        # raise e

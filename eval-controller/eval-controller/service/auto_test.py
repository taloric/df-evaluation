import time
import threading

from common.mysql import update_case_record

from eval_lib.common.exceptions import BadRequestException
from eval_lib.common import logger
from eval_lib.model import const as model_const
from eval_lib.model.base import CaseParams
from eval_lib.databases.mysql.models.models import CaseRecord
from eval_lib.databases.mysql import const as db_const
from config import conf

from common.model import AutoTestCreate, AutoTestUpdate, AutoTestDelete, AutoTestFilter

log = logger.get_logger()
POST_TIMEOUT = 10
# 下发的修改状态请求后，目标预计状态列表。列表中，进行时状态需在完成时状态之前
CR_STATUS_TARGET_MAP = {
    # 暂停请求，预期目标状态为正在暂停和已暂停
    model_const.CASE_PARAMS_STATUS_PAUSE: [
        db_const.CASE_RECORD_STATUS_PAUSING, db_const.CASE_RECORD_STATUS_PAUSED
    ],
    # 取消请求，预期目标状态为正在停止和结束
    model_const.CASE_PARAMS_STATUS_CANCEL: [
        db_const.CASE_RECORD_STATUS_STOPPING,
        db_const.CASE_RECORD_STATUS_FINISHED
    ],
    # 恢复请求，预期目标状态为正在启动和运行
    model_const.CASE_PARAMS_STATUS_RESUME: [
        db_const.CASE_RECORD_STATUS_STARTING,
        db_const.CASE_RECORD_STATUS_STARTED
    ],
    # 重启请求，TODO
    model_const.CASE_PARAMS_STATUS_RESTART: [
        db_const.CASE_RECORD_STATUS_STARTING,
        db_const.CASE_RECORD_STATUS_STARTED
    ],
    model_const.CASE_PARAMS_STATUS_FROCE_END: []
}

# 不同的修改状态请求类型，所支持的当前状态
PARAMS_STATUS_TARGET_MAP = {
    # 暂停请求，仅支持在运行状态时
    model_const.CASE_PARAMS_STATUS_PAUSE: [
        db_const.CASE_RECORD_STATUS_STARTED
    ],
    # 取消请求，仅支持在运行和暂停状态时
    model_const.CASE_PARAMS_STATUS_CANCEL: [
        db_const.CASE_RECORD_STATUS_STARTED, db_const.CASE_RECORD_STATUS_PAUSED
    ],
    # 恢复请求，仅支持在暂停状态时
    model_const.CASE_PARAMS_STATUS_RESUME: [
        db_const.CASE_RECORD_STATUS_PAUSED
    ],
    # 重启请求，TODO
    model_const.CASE_PARAMS_STATUS_RESTART: [
        db_const.CASE_RECORD_STATUS_PAUSED
    ],
    # 强制结束请求，支持所有状态
    model_const.CASE_PARAMS_STATUS_FROCE_END: [
        db_const.CASE_RECORD_STATUS_INIT, db_const.CASE_RECORD_STATUS_STARTED,
        db_const.CASE_RECORD_STATUS_PAUSED,
        db_const.CASE_RECORD_STATUS_STARTING,
        db_const.CASE_RECORD_STATUS_PAUSING,
        db_const.CASE_RECORD_STATUS_STOPPING,
        db_const.CASE_RECORD_STATUS_ERROR, db_const.CASE_RECORD_STATUS_FINISHED
    ]
}

UPDATE_LOCK = threading.RLock()


class AutoTest(object):

    def __init__(self, queue) -> None:
        self.queue = queue

    def Post(self, info: AutoTestCreate):
        """
        将测试创建消息发布到队列，并等待直到相关测试用例记录创建完成。

        参数:
        - info: AutoTestCreate 类型，包含测试用例的创建信息。

        返回值:
        - crs: CaseRecord 查询结果，如果测试用例记录创建成功则返回该记录。
        """
        # 记录日志信息，将消息放入队列
        with UPDATE_LOCK:
            crs = self.Get(
                AutoTestFilter(
                    status=[
                        db_const.CASE_RECORD_STATUS_INIT,
                        db_const.CASE_RECORD_STATUS_STARTED,
                        db_const.CASE_RECORD_STATUS_STARTING,
                        db_const.CASE_RECORD_STATUS_PENDING,
                        db_const.CASE_RECORD_STATUS_PAUSED,
                        db_const.CASE_RECORD_STATUS_PAUSING,
                        db_const.CASE_RECORD_STATUS_STOPPING
                    ]
                )
            )
            if len(crs) >= conf.runner_max_num:
                raise BadRequestException("runner_max_num reached")
                # 创建一个新的测试用例记录，并保存到数据库
            msg = CaseParams(info.to_json())
            cr = CaseRecord(
                uuid=msg.uuid, case_name=msg.case_name,
                process_num=msg.process_num,
                status=db_const.CASE_RECORD_STATUS_INIT
            )
            cr.save()
            log.info(f"put msg to manager: {msg}")
            msg.status = model_const.CASE_PARAMS_STATUS_CREATE

            self.queue.put(msg)

        # 设置等待超时时间
        wait_count = POST_TIMEOUT
        at_filter = AutoTestFilter(uuid=msg.uuid)

        # 循环等待，直到测试用例记录被创建或超时
        while wait_count:
            crs = self.Get(info=at_filter)
            if crs:
                return crs
            time.sleep(1)  # 每秒检查一次
            wait_count -= 1
        return self.Get()

    def Get(self, info: AutoTestFilter = None) -> list:
        """
        根据提供的过滤条件获取测试用例记录列表。
        
        参数:
        - info: AutoTestFilter 类型，可选，用于指定获取测试用例的过滤条件。
        
        返回值:
        - list: 包含满足过滤条件的测试用例记录的列表。
        """
        crs = []

        # 默认只选择未被删除的测试用例记录
        not_delted_where_clause = CaseRecord.deleted == db_const.CASE_RECORD_NOT_DELETED

        if info:
            # 将过滤条件转换为 JSON 格式
            json_where = info.to_json()
            # 根据 JSON 格式的过滤条件生成 WHERE 子句
            where_clause = CaseRecord.visible_where_clause(json_where)
            # 如果过滤条件中包含删除状态，则加上未被删除的限制
            if json_where.get("deleted"):
                where_clause = (where_clause) & (not_delted_where_clause)
            # 根据 WHERE 子句查询满足条件的测试用例记录
            crs = CaseRecord.select().where(where_clause)
        else:
            # 未提供过滤条件时，只选择未被删除的测试用例记录
            crs = CaseRecord.select().where(not_delted_where_clause)

        # 将查询结果转换为列表并返回
        return [cr for cr in crs]

    def Update(self, info: AutoTestUpdate):
        """
        根据提供的AutoTestUpdate信息更新测试状态或记录。
    
        参数:
        - info: AutoTestUpdate对象，包含需要更新的信息，如状态和UUID列表。
    
        返回:
        - 返回调用Get方法的结果，该结果基于AutoTestFilter过滤条件获取。
        """
        if info.status is not None:
            if info.status not in [PARAMS_STATUS_TARGET_MAP.keys()]:
                raise BadRequestException("status is invalid")
            at_filter = AutoTestFilter(uuids=info.uuids)
            # 更新锁。每次更新状态时，需要加锁，防止多个线程同时更新状态
            with UPDATE_LOCK:
                # 根据info中的状态，获取对应的CR_STATUS_TARGET_MAP列表
                cr_target_status_list = CR_STATUS_TARGET_MAP.get(info.status)
                crs = self.Get(info=at_filter)
                need_update_crs = []
                for cr in crs:
                    if cr.status not in cr_target_status_list and cr.status in PARAMS_STATUS_TARGET_MAP.get(
                        info.status
                    ):
                        need_update_crs.append(cr)
                if not need_update_crs:
                    raise BadRequestException(
                        "no test cases available to modify the status"
                    )

                # 遍历info中的UUID列表，为每个UUID创建CaseParams消息并放入队列
                for cr in need_update_crs:
                    uuid = cr.uuid
                    msg = CaseParams(uuid=uuid, status=info.status)
                    log.info(f"put msg to manager: {msg}")
                    self.queue.put(msg)

                # 设置等待超时时间
                wait_count = POST_TIMEOUT
                # 循环等待，直到所有相关测试记录的状态都符合预期
                while wait_count:
                    complete = 1
                    crs = self.Get(info=at_filter)
                    # 检查所有相关记录的状态是否都已更新
                    for cr in crs:
                        if cr.status not in cr_target_status_list:
                            complete = 0
                    if complete:
                        break
                    time.sleep(1)
                    wait_count -= 1
        else:
            # 如果info中的状态为None，则从info中构建json_data，并更新CaseRecord表
            json_data = info.to_json()
            uuids = json_data.pop("uuids")
            CaseRecord.update(**json_data).where(CaseRecord.uuid in uuids
                                                 ).execute()
        # 返回根据at_filter过滤得到的结果
        return self.Get(info=at_filter)

    def Delete(self, info: AutoTestDelete):
        with UPDATE_LOCK:
            for uuid in info.uuids:
                msg = CaseParams(
                    uuid=uuid, status=model_const.CASE_PARAMS_STATUS_FROCE_END
                )
                self.queue.put(msg)
                update_case_record(uuid, deleted=db_const.CASE_RECORD_DELETED)
        return self.Get()

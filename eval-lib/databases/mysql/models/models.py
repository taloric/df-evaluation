import datetime
from peewee import CharField, DateTimeField, IntegerField

from .base import BaseModel
from ..const import COMPONENT_TYPE_UNKNOWN, COMPONENT_TYPE_DF_AGENT, COMPONENT_TYPE_DF_SERVER
from ..db import db


class CaseRecord(BaseModel):
    """
    测试用例记录类

    属性:
        uuid: 用例唯一标识符，字符串类型，最大长度64，不能为空
        case_name: 用例名称，字符串类型，最大长度64，不能为空
        case_params: 用例参数，字符串类型，最大长度1024，不能为空
        user: 执行用户，字符串类型，可以为空
        runner_commit_id: 执行器提交ID，字符串类型，最大长度64，不能为空
        runner_image_tag: 执行器镜像标签，字符串类型，最大长度64，不能为空
        status: 执行状态，整数类型，不能为空
        deleted: 删除状态，整数类型，不能为空
        created_at: 创建时间，日期时间类型，默认为当前时间
    """

    uuid = CharField(max_length=64, unique=True, null=False)
    case_name = CharField(max_length=64, null=False)
    case_params = CharField(max_length=1024, null=False)
    user = CharField(null=True)
    runner_commit_id = CharField(max_length=64, null=True)
    runner_image_tag = CharField(max_length=64, null=True)
    status = IntegerField(null=False)
    deleted = IntegerField(null=False, default=0)
    created_at = DateTimeField(
        formats='%Y-%m-%d %H:%M:%S', default=datetime.datetime.now()
    )

    class Meta:
        table_name = 'case_record'
        database = db


class CaseReport(BaseModel):
    """
    测试例报表类

    属性:
        case_uuid: 测试用例唯一标识符，字符串类型，最大长度64，不能为空
        report_path: 报告路径，字符串类型，最大长度64，不能为空
        created_at: 创建时间，日期时间类型，默认为当前时间
    """

    case_uuid = CharField(max_length=64, null=False)
    report_path = CharField(max_length=64, null=False)
    created_at = DateTimeField(
        formats='%Y-%m-%d %H:%M:%S', default=datetime.datetime.now()
    )

    class Meta:
        table_name = 'case_report'
        database = db


class Component(BaseModel):
    """
    测试组件类

    属性:
        case_uuid: 关联的测试用例唯一标识符，字符串类型，最大长度64，不能为空
        name: 组件名称，字符串类型，最大长度64，不能为空
        type: 组件类型，整数类型，不能为空
        config: 组件配置，字符串类型，最大长度1024，可以为空
        commit_id: 组件提交ID，字符串类型，可以为空
        image_tag: 组件镜像标签，字符串类型，可以为空
        created_at: 创建时间，日期时间类型，默认为当前时间
    """

    case_uuid = CharField(max_length=64, null=False)
    name = CharField(max_length=64, null=False)
    type = IntegerField(
        null=False, default=COMPONENT_TYPE_UNKNOWN, choices=[
            COMPONENT_TYPE_UNKNOWN, COMPONENT_TYPE_DF_AGENT,
            COMPONENT_TYPE_DF_SERVER
        ]
    )
    config = CharField(max_length=1024, null=True)
    commit_id = CharField(null=True)
    image_tag = CharField(null=True)
    created_at = DateTimeField(
        formats='%Y-%m-%d %H:%M:%S', default=datetime.datetime.now()
    )

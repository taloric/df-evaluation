from ..common.exceptions import BadRequestException
from . import const


class BaseStruct:

    KEYS = []

    def __init__(self, json_data: dict = None, **kwargs):
        if not json_data:
            json_data = {}
        self.init(**json_data, **kwargs)

    def init(self, **kwargs):
        for key in self.KEYS:
            if key in kwargs:
                setattr(self, key, kwargs.pop(key))
            else:
                setattr(self, key, None)

    def __getattr__(self, key):
        if key in self.KEYS:
            return None
        else:
            raise AttributeError

    def __str__(self):
        return " ".join([f"{key}:{getattr(self, key)}" for key in self.KEYS])

    def to_json(self):
        return {key: getattr(self, key) for key in self.KEYS}

    def keys(self):
        yield from self.KEYS


class CaseParams(BaseStruct):

    KEYS = ["uuid", "case_name", "process_num", "status", "runner_image_tag"]

    def init(self, **kwargs):
        self.uuid = kwargs.get("uuid", None)
        self.case_name = kwargs.get("case_name", None)
        self.process_num = kwargs.get("process_num", 1)
        self.status = int(
            kwargs.get("status", const.CASE_PARAMS_STATUS_UNKNOWN)
        )
        self.runner_image_tag = kwargs.get("runner_image_tag", "latest")

    def is_valid(self):
        # TODO
        if not self.uuid:
            raise BadRequestException("bad request not uuid")
        if self.status not in const.CASE_PARAMS_STATUS_LIST:
            raise BadRequestException(f"bad request status {self.status}")
        return True

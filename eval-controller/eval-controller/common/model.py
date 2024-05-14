import uuid
from eval_lib.common.exceptions import BadRequestException
from eval_lib.model.base import BaseStruct
from eval_lib.model.const import CASE_PARAMS_STATUS_CREATE, CASE_PARAMS_STATUS_PAUSE, CASE_PARAMS_STATUS_CANCEL, CASE_PARAMS_STATUS_RESUME


class AutoTestCreate(BaseStruct):

    KEYS = ["uuid", "case_name", "process_num", "runner_image_tag"]

    def init(self, **kwargs):
        super().init(**kwargs)
        self.uuid = str(uuid.uuid4())

    def is_valid(self):
        # TODO
        if not (self.uuid):
            raise BadRequestException("bad request")


class AutoTestUpdate(BaseStruct):

    KEYS = ["uuids", "status"]

    def is_valid(self):
        # TODO
        if not self.uuids:
            raise BadRequestException("bad request no uuids")
        if self.status is not None:
            if self.status not in [
                CASE_PARAMS_STATUS_CREATE, CASE_PARAMS_STATUS_PAUSE,
                CASE_PARAMS_STATUS_CANCEL, CASE_PARAMS_STATUS_RESUME
            ]:
                raise BadRequestException(f"bad request status {self.status}")


class AutoTestDelete(BaseStruct):

    KEYS = ["uuids"]

    def is_valid(self):
        # TODO
        if not self.uuids:
            raise BadRequestException("bad request")


class AutoTestFilter(BaseStruct):

    KEYS = ["uuid", "uuids", "status"]


class ResultPostLog(BaseStruct):

    KEYS = ["uuid", "type", "data"]

    def is_valid(self):
        # TODO
        if not self.uuid or self.type is None:
            raise BadRequestException("bad request")
        return True


class ResultGetLog(BaseStruct):

    KEYS = ["uuid", "type", "line_index", "line_size"]

    def init(self, **kwargs):
        super().init(**kwargs)
        self.type = int(self.type) if self.type is not None else self.type
        if not self.line_index:
            self.line_index = 1
        if not self.line_size:
            self.line_size = 100
        self.line_index = int(self.line_index)
        self.line_size = int(self.line_size)

    def is_valid(self):
        # TODO
        if not self.uuid or self.type is None:
            raise BadRequestException("bad request")
        return True


class ResultLogResponse(BaseStruct):

    KEYS = ["uuid", "logs", "line_index", "line_size", "line_count"]


class ResultGetFile(BaseStruct):

    KEYS = ["uuid", "type"]

    def init(self, **kwargs):
        super().init(**kwargs)
        self.type = int(self.type) if self.type is not None else self.type

    def is_valid(self):
        # TODO
        if not self.uuid or self.type is None:
            raise BadRequestException("bad request")
        return True


class ResultFileResponse(BaseStruct):

    KEYS = ["uuid", "files"]

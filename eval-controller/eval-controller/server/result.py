from flask import request, Blueprint
from zipfile import ZipFile

from common.model import ResultPostLog, ResultGetLog, ResultGetFile
from common.utils import json_response, exception_decorate
from common.const import API_PREFIX
from eval_lib.common import logger
from eval_lib.common.exceptions import BadRequestException
from eval_lib.model.const import RESULT_TYPE_LOG_RAW, RESULT_TYPE_PERFORMANCE_MD
from service.result import ResultWorker

result_app = Blueprint('result_app', __name__, url_prefix=API_PREFIX)
log = logger.get_logger()


@result_app.route("/result/zip", methods=["POST"])
@exception_decorate
def post_result_zip():
    if 'file' not in request.files:
        raise BadRequestException("No file part")

    file = request.files['file']
    if file.filename == "":
        raise BadRequestException("No selected file")

    zip_file = ZipFile(file)
    r = ResultWorker().post_zip(filename=file.filename, zipfile=zip_file)
    return json_response(data=r), 200


@result_app.route("/result/log", methods=["POST"])
@exception_decorate
def post_result_log():
    json_data = request.json
    rpl = ResultPostLog(json_data)
    rpl.is_valid()

    if rpl.type != RESULT_TYPE_LOG_RAW:
        raise BadRequestException("File type is not log")
    r = ResultWorker().post_log(rpl)
    return json_response(data=r), 200


@result_app.route("/result/log", methods=["GET"])
@exception_decorate
def get_result_log():
    args = request.args
    rgl = ResultGetLog(**args)
    rgl.is_valid()

    if rgl.type != RESULT_TYPE_LOG_RAW:
        raise BadRequestException("Log File type is not suport")
    r = ResultWorker().get_log(rgl)
    return json_response(data=r), 200


@result_app.route("/result/performance", methods=["GET"])
@exception_decorate
def get_result_performance():
    args = request.args
    rgl = ResultGetFile(**args)
    rgl.is_valid()

    if rgl.type == RESULT_TYPE_PERFORMANCE_MD:
        r = ResultWorker().get_performance_md(rgl)
    else:
        raise BadRequestException("Performance File type is not support")
    return json_response(data=r), 200

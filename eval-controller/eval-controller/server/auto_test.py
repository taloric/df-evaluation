from flask import request, Blueprint
from common.model import AutoTestCreate, AutoTestUpdate, AutoTestDelete, AutoTestFilter
from common.utils import json_response, exception_decorate
from common.const import API_PREFIX
from eval_lib.common import logger
from service.auto_test import AutoTest

auto_test_app = Blueprint('auto_test_app', __name__, url_prefix=API_PREFIX)
log = logger.get_logger()


@auto_test_app.route("/auto-test", methods=["POST"])
@exception_decorate
def exec_tests():
    json_data = request.json
    at = AutoTestCreate(json_data)
    at.is_valid()

    res = AutoTest(auto_test_app.queue).Post(info=at)
    return json_response(data=res), 200


@auto_test_app.route("/auto-test", methods=["PATCH"])
@exception_decorate
def update_test():
    json_data = request.json
    at = AutoTestUpdate(json_data)
    at.is_valid()

    res = AutoTest(auto_test_app.queue).Update(info=at)
    return json_response(data=res), 200


@auto_test_app.route("/auto-test", methods=["DELETE"])
@exception_decorate
def delete_tests():
    json_data = request.json
    at = AutoTestDelete(json_data)
    at.is_valid()

    res = AutoTest(auto_test_app.queue).Update(info=at)
    return json_response(data=res), 200


@auto_test_app.route("/auto-test", methods=["GET"])
@exception_decorate
def get_tests():
    args = request.args
    at = AutoTestFilter(**args)

    res = AutoTest(auto_test_app.queue).Get(info=at)
    return json_response(data=res), 200

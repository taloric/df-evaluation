from flask import Blueprint

from common.const import API_PREFIX
from common.utils import json_response, exception_decorate
from service.dictonary import DictionaryWorker
from eval_lib.common import logger

dictionary_app = Blueprint('dictionary_app', __name__, url_prefix=API_PREFIX)
log = logger.get_logger()


@dictionary_app.route("/dictionary/<resource_name>", methods=['GET'])
@exception_decorate
def get_resource_dictionary(resource_name):
    log.info(f'get_resource_dictionary: {resource_name}')
    res = DictionaryWorker(resource_name).Get()
    return json_response(data=res), 200

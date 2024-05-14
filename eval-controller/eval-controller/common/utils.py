import traceback
import json

from datetime import date
from functools import wraps
from common import const
from eval_lib.common.ssh import SSHPool
from eval_lib.common import logger
from eval_lib.common.exceptions import BadRequestException, InternalServerErrorException
from eval_lib.databases.mysql.models.base import BaseModel

log = logger.get_logger()

ssh_pool_default = SSHPool(
    const.MANAGER_SSH_PORT_DEFAULT,
    const.MANAGER_SSH_USERNAME_DEFAULT,
    const.MANAGER_SSH_PASSWORD_DEFAULT,
)


def exception_decorate(function):

    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)

        except BadRequestException as e:
            log.error(e)
            return json_response(
                status=e.status, description=str(e), wait_callback=False
            ), 400

        except InternalServerErrorException as e:
            log.error(traceback.format_exc())
            return json_response(
                status=e.status, description=str(e), wait_callback=False
            ), 500

        except Exception as e:
            log.error(traceback.format_exc())
            return json_response(
                status="SERVER_ERROR", description=str(e), wait_callback=False
            ), 500

    return wrapper


class EvalEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.to_json()
        elif isinstance(obj, date):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return super(EvalEncoder, self).default(obj)


def json_response(
    status="SUCCESS", description=None, data=None, type=None,
    wait_callback=False, task=None, page=None, flag=None, error_message=None
):
    '''Generate json data for API response

    :param status: response status, HTTP status or specific status
    :param description:
    :param data: resource data
    :types data: list or dict
    :param type:
    :param wait_callback: task synchronization or asynchronous
    :param task:
    :param page:
    :param flag:
    :return:
    '''
    if task is not None:
        wait_callback = True
    data = dict_response(
        status, description, data, type, wait_callback, task, page, flag,
        error_message
    )

    return EvalEncoder().encode(data)


def dict_response(
    status="SUCCESS", description=None, data=None, type=None,
    wait_callback=False, task=None, page=None, flag=None, error_message=None
):
    if description is None:
        description = ''
    if task is not None:
        wait_callback = True
    info = {
        'OPT_STATUS': status,
        'WAIT_CALLBACK': wait_callback,
        'TASK': task,
        'DESCRIPTION': description
    }
    if type is None and data is not None:
        if isinstance(data, list):
            if data:
                type = data[0].__class__.__name__
            else:
                type = None
        else:
            type = data.__class__.__name__
    if type is not None:
        info['TYPE'] = type
    if data is not None:
        info['DATA'] = data
    if page is not None:
        info['PAGE'] = page
    if flag is not None:
        info['FLAG'] = flag
    if error_message is not None:
        info['ERROR_MESSAGE'] = error_message
    return info

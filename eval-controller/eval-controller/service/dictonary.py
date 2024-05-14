from eval_lib.source.dictonary import Dictionary
from eval_lib.common import logger
from eval_lib.common.exceptions import BadRequestException

log = logger.get_logger()


class DictionaryWorker(object):

    def __init__(self, resource_name):
        self.resource_name = resource_name
        self.data = []

    def Get(self):
        dct = Dictionary()
        try:
            dict_name = f"{self.resource_name.upper()}_DICTIONARY"
            raw_data = getattr(dct, dict_name)
            self.data = [[key] + values for key, values in raw_data.items()]
        except AttributeError as e:
            log.error(e)
            raise BadRequestException("resource_name is not exist")
        return self.data

from flask import Flask
from multiprocessing import Process
from eval_lib.common import logger
from .auto_test import auto_test_app
from .result import result_app
from .dictionary import dictionary_app
from config import conf

app = Flask(__name__)
log = logger.get_logger()
app.register_blueprint(auto_test_app)
app.register_blueprint(result_app)
app.register_blueprint(dictionary_app)


class ServerProcess(Process):

    def __init__(self, queue):
        auto_test_app.queue = queue
        super().__init__()

    def run(self):
        app.run(host="0.0.0.0", port=conf.listen_port)

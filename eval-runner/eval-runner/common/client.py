import requests
import threading
import time
import json
from eval_lib.model.const import RESULT_TYPE_LOG_RAW
from eval_lib.common.logger import get_logger
log = get_logger()


class ResultClient():
    # 将测试结果文件 传输到controller
    def __init__(self, server_url) :
        self.server_url = server_url

    def send_result_zip(self, zip_file_path):
        try:
            with open(zip_file_path, 'rb') as file:
                files = {'file': file}
                response = requests.post(f'{self.server_url}', files=files)
                if response.status_code == 200:
                    log.info("Result files uploaded successfully!")
                else:
                    log.error(f"Upload failed: {response.text}")
        except Exception as e:
            log.error(f"Upload failed: {e}")


class LogClient(threading.Thread):
    # 将测试过程log 传输到controller
    def __init__(self, uuid, log_file, server_url):
        super().__init__()
        self.uuid = uuid
        self.log_file = log_file
        self.server_url = server_url
        self.last_position = 0 
        self._stop_event = threading.Event()
    
    def stop(self):
        self._stop_event.set()

    def send_log(self):
        headers = {
        'Content-Type': 'application/json'
        }
        with open(self.log_file, 'r') as file:
            file.seek(self.last_position)  # 定位到上一次发送的位置
            new_log_data = file.read()
            payload = json.dumps({
                "uuid": self.uuid,
                "type": RESULT_TYPE_LOG_RAW,
                "data": new_log_data
            })
            if new_log_data:
                response = requests.request("POST", self.server_url, headers=headers, data=payload)
                if response.status_code == 200:
                    log.info("New log sent successfully.")
                    # 更新上一次发送的位置
                    self.last_position = file.tell()
                else:
                    log.error(f"Failed to send new log error:{response.text}")
            else:
                log.info("No new log to send.")
    
    def run(self):
        while not self._stop_event.is_set():
            self.send_log()
            time.sleep(5)
        self.send_log()
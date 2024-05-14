import paramiko
from typing import Dict

DEFAULT_TIMEOUT = 20 * 60


class SSHClient(paramiko.SSHClient):

    def exec_command(self, command, timeout=DEFAULT_TIMEOUT):
        return super().exec_command(command, timeout=timeout)


class SSHPool(object):
    pool: Dict[str, paramiko.SSHClient] = {}

    def __init__(
        self, default_port=22, default_username=None, default_password=None
    ):
        self.default_port = default_port
        self.default_username = default_username
        self.default_password = default_password

    def connect(self, ip, port, username, password):
        ssh_client = SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_client.connect(ip, port, username, password)
        except paramiko.SSHException as e:
            return None
        return ssh_client

    def get(self, ip, port=None, username=None, password=None) -> SSHClient:
        port = port or self.default_port
        username = username or self.default_username
        password = password or self.default_password
        ssh_client = self.pool.get(ip)
        if ssh_client and ssh_client.get_transport(
        ) and ssh_client.get_transport().is_active():
            return ssh_client
        ssh_client = self.connect(ip, port, username, password)
        self.pool[ip] = ssh_client
        return ssh_client

    def close(self):
        for ssh_client in self.pool.values():
            ssh_client.close()
        self.pool.clear()

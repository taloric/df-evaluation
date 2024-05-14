from eval_lib.model.base import BaseStruct


class AgentMeta(BaseStruct):

    KEYS = ["agent_ip", "version", "ssh_port", "ssh_username", "ssh_password"]

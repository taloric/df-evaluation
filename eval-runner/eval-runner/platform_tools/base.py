

class PlatformBase():
    def __init__(self) -> None:
        pass
    
    @staticmethod
    def create_instances(instance_names: list, image_id="", instance_type="") -> dict:
        '''创建实例
        return:
            {
                "instance_name": "ip"
            }
        '''
        pass

    @staticmethod
    def delete_instances(instance_names: list):
        '''删除实例
        '''
        pass

    @staticmethod
    def start_instances(instance_names: list):
        pass

    @staticmethod
    def stop_instances(instance_names: list):
        pass
    
    @staticmethod
    def get_instance_status(instance_name: str):
        pass

    @staticmethod
    def get_instance_ip(instance_name: str):
        pass

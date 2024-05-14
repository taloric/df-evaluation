import os
from platform_tools.aliyun import ali_const
from common import const
from typing import List
from platform_tools.base import PlatformBase
from Tea.core import TeaCore
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util.client import Client as UtilClient
from alibabacloud_ecs20140526 import models as ecs_models
from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_darabonba_number.client import Client as NumberClient

from eval_lib.common.logger import get_logger

log = get_logger()


class Aliyun(PlatformBase):

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def create_client() -> EcsClient:
        """
        使用AK&SK初始化账号Client
        @param access_key_id:
        @param access_key_secret:
        @return: Client
        """
        config = open_api_models.Config(
            # 必填，请确保代码运行环境设置了环境变量 ALICLOUD_ACCESS_KEY. ,
            access_key_id=os.environ['ALICLOUD_ACCESS_KEY'],
            # 必填，请确保代码运行环境设置了环境变量 ALICLOUD_SECRET_KEY. ,
            access_key_secret=os.environ['ALICLOUD_SECRET_KEY'],
            # 必填，请确保代码运行环境设置了环境变量 ALICLOUD_REGION. ，
            region_id=os.environ['ALICLOUD_REGION'],
        )
        return EcsClient(config)

    @staticmethod
    def _start_instances(
        client: EcsClient,
        region_id: str,
        instance_ids: List[str],
        dry_run: bool = False,
    ) -> None:
        """
        [批量] 实例开机-> None
        """
        request = ecs_models.StartInstancesRequest(
            dry_run=dry_run, region_id=region_id, instance_id=instance_ids
        )
        responce = client.start_instances(request)
        log.info(
            f'start instance: {instance_ids}, Successfully. result: {UtilClient.to_jsonstring(TeaCore.to_map(responce.body))}'
        )

    @staticmethod
    def _stop_instances(
        client: EcsClient,
        region_id: str,
        instance_ids: List[str],
        stopped_mode: str = 'KeepCharging',
        dry_run: bool = False,
    ) -> None:
        """
        [批量] 实例关机->  None
        """
        request = ecs_models.StopInstancesRequest(
            region_id=region_id,
            instance_id=instance_ids,
            stopped_mode=stopped_mode,
            dry_run=dry_run,
        )
        runtime = util_models.RuntimeOptions()
        responce = client.stop_instances_with_options(request, runtime)
        log.info(
            f'stop instance: {instance_ids}, successful. result：{UtilClient.to_jsonstring(TeaCore.to_map(responce.body))}'
        )

    @staticmethod
    def _create_instances(
        client: EcsClient,
        image_id: str,
        instance_name: str,
        region_id: str,
        instance_type: str,
        security_group_id: str,
        v_switch_id: str,
        resource_group_id: str,
        password: str,
        zone_id: str,
        key_pair_name: str,
        amount: int,
    )-> List[str]:
        """
        [批量] 实例创建->  str: 实例id
        """
        tag_0 = ecs_models.RunInstancesRequestTag(
            key='财务单元',
            value='自动化测试'
        )
        request = ecs_models.RunInstancesRequest(
            region_id=region_id,
            instance_name=instance_name,
            image_id=image_id,
            instance_type=instance_type,
            security_group_id=security_group_id,
            v_switch_id=v_switch_id,
            resource_group_id=resource_group_id,
            password=password,
            zone_id=zone_id,
            key_pair_name=key_pair_name,
            amount=amount,
            tag=[tag_0],
        )
        runtime = util_models.RuntimeOptions()
        response = client.run_instances_with_options(request, runtime)
        instance_ids = UtilClient.to_jsonstring(
            response.body.instance_id_sets.instance_id_set
        )
        UtilClient.sleep(40000)
        log.info(
            f'-----------create instance successful, instance ID:{instance_ids}--------------'
        )
        return instance_ids
    
    @staticmethod
    def _delete_instances(
        client: EcsClient,
        region_id: str,
        instance_ids: List[str],
        force: bool = False,
    ) -> None:
        """
        [批量] 实例删除->  None
        """
        Aliyun._stop_instances(client, region_id, instance_ids)
        Aliyun._await_instances_status(
            client, region_id, instance_ids, "Stopped"
        )
        request = ecs_models.DeleteInstancesRequest(
            region_id=region_id,
            instance_id=instance_ids,
            force=force,
        )
        runtime = util_models.RuntimeOptions()
        response = client.delete_instances_with_options(request, runtime)
        log.info(
            '--------------------instance delete successful--------------------'
        )
        log.info(UtilClient.to_jsonstring(UtilClient.to_map(response)))

    @staticmethod
    def _await_instances_status(
        client: EcsClient,
        region_id: str,
        instance_ids: List[str],
        expect_instance_status: str,
    ) -> bool:
        """
        [批量] 等待实例状态为特定的状态, 默认等待20s，超过20s返回false，否则返回true。
        """
        time = 0
        flag = True
        while flag and NumberClient.lt(time, 10):
            flag = False
            instances_info= Aliyun._get_instances_info(
                client, region_id, instance_ids
            )
            for instance in instances_info:
                instance_status = instance["status"]
                log.info(
                    f'instance: {instance["instanceid"]}, status: {instance_status}'
                )
                if not UtilClient.equal_string(
                    instance_status, expect_instance_status
                ):
                    UtilClient.sleep(3000)
                    flag = True
            time = NumberClient.add(time, 1)
        return NumberClient.lt(time, 10)

    @staticmethod
    def _get_instances_info(        
        client: EcsClient, region_id: str, instance_ids: List[str]
    ) -> List[dict]:
        """
        [批量] 获取实例信息
        返回字典列表[{"instanceid","ip":"","status":""},]
        """
        instance_info = []
        request = ecs_models.DescribeInstancesRequest(
            region_id=region_id, instance_ids=str(instance_ids)
        )
        runtime = util_models.RuntimeOptions()
        response = client.describe_instances_with_options(request, runtime)
        instance_data = response.body.instances.instance
        for instance in instance_data:
            instance_info.append(
                {
                    "instanceid": instance.instance_id,
                    "ip": instance.vpc_attributes.private_ip_address.ip_address[0],
                    "status": instance.status,
                }
            )
        return instance_info
    
    @staticmethod
    def _get_instance_id_by_name(
        client: EcsClient, 
        region_id: str, 
        instance_name: str
    ) -> str:
        describe_instances_request = ecs_models.DescribeInstancesRequest(
            region_id=region_id,
            instance_name=instance_name
        )
        runtime = util_models.RuntimeOptions()
        response = client.describe_instances_with_options(describe_instances_request, runtime)
        if response.body.instances.instance:
            return response.body.instances.instance[0].instance_id
        else:
            return ""

    @staticmethod
    def create_instances(
        instance_names: list,
        image_id=ali_const.ali_image_id_arm, 
        instance_type=ali_const.ali_instance_type_c6r_2x_large,
    ) -> dict:
        '''创建通用镜像的实例
        密码固定为CASE_SSH_PASSWORD_DEFAULT
        '''
        client = Aliyun.create_client()
        region_id=os.environ['ALICLOUD_REGION']
        instances_ip = {}
        for instance_name in instance_names:
            instance_ids = Aliyun._create_instances(
                client=client,
                instance_name=instance_name,
                image_id=image_id,
                instance_type=instance_type,
                region_id=region_id,
                security_group_id=ali_const.ali_security_group_id_default,
                v_switch_id=ali_const.ali_v_switch_id_beijing_k,
                resource_group_id=ali_const.ali_resource_group_id_default,
                password=const.CASE_SSH_PASSWORD_DEFAULT,
                zone_id=ali_const.ali_zone_id_beijing_k,
                key_pair_name=ali_const.ali_key_pair_name_default,
                amount=1,
            )
            Aliyun._await_instances_status(
                client, region_id, instance_ids, "Running"
            )
            instances_info = Aliyun._get_instances_info(
                client=client,
                region_id=region_id,
                instance_ids=instance_ids,
            )
            instances_ip[instance_name] = instances_info[0]["ip"]
        log.info(f"create instances successful: {instances_ip}")
        return instances_ip

    @staticmethod
    def delete_instances(instance_names: list):
        instance_ids = []
        client = Aliyun.create_client()
        region_id=os.environ['ALICLOUD_REGION']
        for instance_name in instance_names:
            instance_id = Aliyun._get_instance_id_by_name(
                client=client,
                region_id=region_id,
                instance_name=instance_name
            )
            if instance_id:
                instance_ids.append(instance_id)
        Aliyun._delete_instances(
            client=client,
            region_id=region_id,
            instance_ids=instance_ids,
        )
import allure
import os
import time
import re
import zipfile

from scp import SCPClient

from eval_lib.common.logger import get_logger
from eval_lib.common.ssh import SSHPool
from eval_lib.databases.redis import runner_info
from eval_lib.databases.redis import const as redis_const
from common.module import AgentMeta
from common import const
from common.config import conf
from platform_tools.aliyun.aliyun_sdk import Aliyun
from platform_tools.base import PlatformBase
from agent_tools.deepflow_agent.deepflow_agent import DeeepflowAgent
from agent_tools.base import AgentBase

ssh_pool_default = SSHPool(
    const.CASE_SSH_PORT_DEFAULT,
    const.CASE_SSH_USERNAME_DEFAULT,
    const.CASE_SSH_PASSWORD_DEFAULT,
)
redis_db = runner_info.RedisRunnerInfo(
    host=conf.redis_host, port=conf.redis_port, password=conf.redis_password,
    db=conf.redis_db, max_connections=10
)
log = get_logger()

def get_case_uuid():
    return conf.case_params.uuid[:8]

def step(title):
    """
    执行一个步骤，并根据Redis中存储的运行状态来决定步骤的执行流程。

    :param title: 步骤的标题，用于日志记录和报告。
    :return: 执行allure步骤后的结果。
    """
    log.info(title)  # 记录步骤开始的日志
    while True:
        # 从Redis获取运行者信息
        runner_info_dict = redis_db.get_runner_info(uuid=conf.case_params.uuid)
        log.info(runner_info_dict)
        case_status = runner_info_dict.get("case-status", None)
        case_control_status = runner_info_dict.get("case-control-status", None)
        # 检查是否需要主动暂停用例
        if case_control_status == redis_const.CASE_STATUS_PAUSED:
            log.info(f"case pause proactively")
            # 如果当前状态不是暂停状态，则更新状态为暂停
            if case_status != redis_const.CASE_STATUS_PAUSED:
                redis_db.update_runner_info(
                    uuid=conf.case_params.uuid,
                    info={"case-status": redis_const.CASE_STATUS_PAUSED}
                )
                case_status = redis_const.CASE_STATUS_PAUSED

        # 检查是否需要主动取消用例
        elif case_control_status == redis_const.CASE_STATUS_CANCELLED:
            log.info(f"case cancel proactively")
            # 如果当前状态不是取消状态，则更新状态为取消
            if case_status != redis_const.CASE_STATUS_CANCELLED:
                redis_db.update_runner_info(
                    uuid=conf.case_params.uuid,
                    info={"case-status": redis_const.CASE_STATUS_CANCELLED}
                )
                case_status = redis_const.CASE_STATUS_CANCELLED
        
        elif case_control_status == redis_const.CASE_STATUS_RUNNING:
            # 如果当前状态不是运行状态，则更新状态为运行
            if case_status != redis_const.CASE_STATUS_RUNNING:
                redis_db.update_runner_info(
                    uuid=conf.case_params.uuid,
                    info={"case-status": redis_const.CASE_STATUS_RUNNING}
                )
                case_status = redis_const.CASE_STATUS_RUNNING

        # 如果用例状态不是运行中，则每隔20秒检查一次；如果是，则结束循环
        if case_status != redis_const.CASE_STATUS_RUNNING:
            time.sleep(20)
        else:
            break
    # 执行allure步骤，并返回结果
    return allure.step(title)


def choose_platform() -> PlatformBase:
    platform_type = conf.platform_tools.get("type", "")
    if platform_type == 'aliyun':
        aliyun_info = conf.platform_tools.get("aliyun", {})
        if 'ALICLOUD_ACCESS_KEY' not in os.environ:
            os.environ['ALICLOUD_ACCESS_KEY'] = aliyun_info['access_key']

        if 'ALICLOUD_SECRET_KEY' not in os.environ:
            os.environ['ALICLOUD_SECRET_KEY'] = aliyun_info['secret_key']

        if 'ALICLOUD_REGION' not in os.environ:
            os.environ['ALICLOUD_REGION'] = aliyun_info['region']
        return Aliyun
    else:
        # 如果没有选择有效的平台，则记录错误并返回 None
        log.error("Invalid platform type specified.")
        return None


def choose_agent(agent_ip) -> AgentBase:
    agent_type = conf.agent_tools.get("type", "")
    agent_conf = conf.agent_tools.get(agent_type, {})
    agent_version = agent_conf['version']
    if agent_type == 'deepflow':
        agent_meta = AgentMeta()
        agent_meta.ssh_port = const.CASE_SSH_PORT_DEFAULT
        agent_meta.ssh_password = const.CASE_SSH_PASSWORD_DEFAULT
        agent_meta.ssh_username = const.CASE_SSH_USERNAME_DEFAULT
        agent_meta.agent_ip = agent_ip
        agent_meta.version = agent_version
        agent = DeeepflowAgent()
        agent.init(agent_meta)
        return agent
    else:
        # 如果没有选择有效的 agent，则记录错误并返回 None
        log.error("Invalid agent type specified.")
        return None


def install_unzip(vm_ip, ssh_pool: SSHPool = ssh_pool_default):
    """
    通过SSH在指定的虚拟机上安装unzip工具。
    
    参数:
    - vm_ip: 要安装unzip工具的虚拟机IP地址。
    - ssh_pool: SSH连接池，用于管理SSH连接。默认为ssh_pool_default。
    
    返回值:
    无返回值。
    """
    # 从SSH连接池获取指定IP的SSH客户端
    ssh_client = ssh_pool.get(vm_ip)
    # 检查unzip是否已经安装
    check_command = 'which unzip'
    _, stdout, _ = ssh_client.exec_command(check_command)
    # 如果已安装，则记录日志并返回
    if stdout.channel.recv_exit_status() == 0:
        log.info('Unzip already installed on')
        return
    # 获取系统信息，用于后续根据系统类型安装unzip
    system_name, _ = get_system_info(vm_ip, ssh_pool)
    # 根据系统类型选择安装命令
    if 'CentOS' in system_name:
        install_command = 'yum install -y unzip'
    elif 'Ubuntu' in system_name or 'Debian' in system_name:
        install_command = 'apt-get install -y unzip'
    elif 'Amolis' in system_name:
        install_command = 'dnf install -y unzip'
    else:
        # 如果系统不受支持，则记录错误日志并返回
        log.error(f'Unsupported system: {system_name}')
        return
    # 执行安装命令
    _, stdout, stderr = ssh_client.exec_command(install_command)
    # 获取命令执行状态，并根据状态记录成功或失败的日志
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        log.info('Unzip installed successfully on')
    else:
        log.error(
            f'Failed to install unzip, error log:{stderr.read().decode()}'
        )


def get_system_info(vm_ip, ssh_pool: SSHPool = ssh_pool_default) -> tuple:
    """
    通过SSH连接到指定的虚拟机IP地址，获取操作系统的名称和版本信息。
    
    参数:
    vm_ip (str): 要连接的虚拟机的IP地址。
    ssh_pool (SSHPool): SSH连接池，默认为ssh_pool_default。用于管理SSH连接。
    
    返回:
    tuple: 包含操作系统的名称和版本的元组。(name, version)
    """
    # 从SSH连接池中获取指定IP的SSH客户端
    ssh_client = ssh_pool.get(vm_ip)
    # 在虚拟机上执行命令，获取操作系统名称和版本的信息
    _, stdout, stderr = ssh_client.exec_command(
        "cat /etc/os-release | grep -E '^NAME=|^VERSION='"
    )
    name = ""
    version = ""
    # 解析命令输出，提取操作系统名称和版本
    for line in stdout:
        if line.startswith('NAME='):
            name = line.split('=')[1].strip()
        elif line.startswith('VERSION='):
            version = line.split('=')[1].strip()
    # 如果未能成功提取名称或版本，记录警告日志
    if not name or not version:
        log.warning(
            'Failed to get system info, error log:',
            stderr.read().decode()
        )
    # 返回操作系统名称和版本
    return name, version


def upload_files(
    vm_ip, local_path, remote_path, ssh_pool: SSHPool = ssh_pool_default
) -> bool:
    '''
    上传文件到远程服务器。
    
    参数:
    - vm_ip: 远程服务器的IP地址。
    - local_path: 本地文件或目录的路径。
    - remote_path: 远程服务器上文件或目录的目标路径（目录必须存在）。
    - ssh_pool: SSH连接池，默认使用 ssh_pool_default。
    
    返回值:
    - bool: 上传成功返回True，失败返回False。
    '''
    # 从SSH连接池获取SSH客户端
    ssh_client = ssh_pool.get(vm_ip)
    try:
        # 使用SCPClient上传文件或目录
        with SCPClient(
            ssh_client.get_transport(), socket_timeout=15.0
        ) as scpclient:
            # 判断本地路径是文件还是目录，并分别处理
            if os.path.isfile(local_path):
                # 上传文件
                scpclient.put(local_path, remote_path)
                log.info(f'Upload file success: {local_path} -> {remote_path}')
                return True
            elif os.path.isdir(local_path):
                # 上传目录下所有文件
                files_uploaded = 0
                for filename in os.listdir(local_path):
                    file_path = os.path.join(local_path, filename)
                    if os.path.isfile(file_path):
                        scpclient.put(file_path, remote_path)
                        log.info(
                            f'Upload file success: {file_path} -> {remote_path}'
                        )
                        files_uploaded += 1
                # 记录上传文件总数
                log.info(
                    f'Total {files_uploaded} files uploaded from {local_path} to {remote_path}'
                )
                return True
            else:
                # 处理本地路径无效的情况
                log.error(f'Invalid local path: {local_path}')
                return False
    except FileNotFoundError:
        # 处理本地文件或目录不存在的情况
        log.error(f'Local file or directory not found: {local_path}')
        return False
    except Exception as e:
        # 处理其他异常
        log.error(f'Upload file error: {e}')
        return False


def install_k8s(vm_ip, ssh_pool: SSHPool = ssh_pool_default):
    """
    安装Kubernetes集群。
    
    通过SSH连接到指定的虚拟机IP地址，执行安装Kubernetes的命令，并监控安装过程直到集群达到Ready状态。
    
    参数:
    - vm_ip: 要安装Kubernetes的虚拟机的IP地址。
    - ssh_pool: 用于SSH连接的池，默认为ssh_pool_default。
    
    返回值:
    无返回值。安装成功会打印日志信息，失败则抛出异常。
    """
    ssh_client = ssh_pool.get(vm_ip)  # 从SSH池中获取一个客户端实例

    try:
        # 构造安装Kubernetes和Calico的命令
        cmd_install = '''sealos run localhost/labring/kubernetes:v1.25.0 localhost/calico:v3.24.1 --single && \
                         kubectl taint node node-role.kubernetes.io/control-plane- --all'''
        log.info(f'install k8s, cmd: {cmd_install}')
        _, stdout, stderr = ssh_client.exec_command(cmd_install)  # 执行安装命令
        exit_status = stdout.channel.recv_exit_status()  # 获取命令执行的状态
        if exit_status == 0:
            log.info(f'{cmd_install} exec successful')
        else:
            # 如果命令执行失败，记录错误日志
            log.error(
                f'abnormal installation of k8s, error: {stderr.read().decode()}'
            )

        # 循环检查Kubernetes节点状态，直到所有节点Ready
        for _ in range(30):
            cmd_get_nodes = "kubectl get nodes"
            log.info(f"check the status of k8s, cmd: {cmd_get_nodes}")
            _, stdout, stderr = ssh_client.exec_command(
                cmd_get_nodes
            )  # 执行命令获取节点状态
            output = stdout.read().decode()  # 命令输出
            error = stderr.read().decode()  # 错误信息
            if re.search(r"\bReady\b", output):  # 检查输出中是否有"Ready"关键词
                log.info("k8s installation completed")
                break
            # 如果节点未就绪，记录日志并等待一段时间后再次检查
            log.error(
                f'wait k8s ready: info: {output}, wait about 5s, err: {error}'
            )
            time.sleep(5)
        else:
            # 如果30次检查都未达到Ready状态，则断言失败
            assert False
    except Exception as err:
        # 如果安装过程中出现异常，记录错误日志并断言失败
        log.error(
            'install kubernetes unsuccessful or the cluster status is abnormal, err: {}'
            .format(err)
        )
        assert False


def ensure_process_running(
    vm_ip, process_name, ssh_pool: SSHPool = ssh_pool_default
):
    """
    确保指定的进程在远程虚拟机上运行。
    
    参数:
    - vm_ip: 远程虚拟机的IP地址。
    - process_name: 需要确保运行的进程名称。
    - ssh_pool: SSH连接池，用于远程操作虚拟机。默认为ssh_pool_default。
    
    返回值:
    无返回值。如果进程成功启动并运行，则记录日志信息；如果启动失败，则记录错误日志并抛出断言错误。
    """
    # 通过SSH连接池获取远程虚拟机的SSH客户端
    ssh_client = ssh_pool.get(vm_ip)
    # 构造启动并检查进程状态的命令
    check_cmd = f'systemctl start {process_name} && systemctl status {process_name}'
    # 执行命令，获取执行结果
    _, stdout, stderr = ssh_client.exec_command(check_cmd)
    # 读取并解码标准输出的内容
    output = stdout.read().decode()
    # 检查进程是否成功启动并运行
    if "Active: active (running)" in output:
        log.info(f"{process_name} successfully started and is running")
    else:
        # 如果进程启动失败，记录错误日志并抛出断言错误
        log.error(
            f"{process_name} start failed, err: {stderr.read().decode()}"
        )
        assert False


def zip_dir(folder_path, output_path):
    """
    将指定文件夹压缩成ZIP文件。
    
    :param folder_path: 需要压缩的文件夹路径。
    :param output_path: 压缩文件输出的路径。
    """
    # 创建一个ZIP文件对象，准备写入压缩文件
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 遍历folder_path下的所有文件和子文件夹
        for root, dirs, files in os.walk(folder_path):
            # 遍历子文件夹，并将其添加到压缩文件中
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                # 将目录添加到压缩文件，使用相对路径
                zipf.write(
                    dir_path,
                    os.path.relpath(dir_path, os.path.dirname(folder_path))
                )
            # 遍历文件，并将其添加到压缩文件中
            for file in files:
                file_path = os.path.join(root, file)
                # 将文件添加到压缩文件，使用相对路径
                zipf.write(
                    file_path,
                    os.path.relpath(file_path, os.path.dirname(folder_path))
                )

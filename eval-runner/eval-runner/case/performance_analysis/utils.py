import re
from common.utils import ssh_pool_default
from eval_lib.common.ssh import SSHPool
from eval_lib.databases.influx.influx_db import InfulxDB
from common.const import TELEGRAF_TABLE_NAME_IN_INFLUX
from eval_lib.common.logger import get_logger

log = get_logger()

def format_latency(time_str, target_unit):
    units = {'us': 0.000001, 'µs': 0.000001, 'ms': 0.001, 's': 1}
    time_str = time_str.strip()
    try:
        pattern = r"[^\d]*$"
        match = re.search(pattern, time_str)
        matched_position = match.start()
        time_value, current_unit = time_str[:matched_position], match.group()
        time_value = float(time_value)

        if current_unit not in units:
            log.error(f"Invalid current time unit: {current_unit}")
            return None
        converted_time = round(
            time_value * units[current_unit] / units[target_unit], 3
        )
        return str(converted_time) + target_unit

    except ValueError as e:
        log.info(f"Error: {e}")
        return None
    
def get_traffic_tool_data(
    vm_ip, ssh_pool: SSHPool=ssh_pool_default
):
    result = {}
    ssh_client = ssh_pool.get(vm_ip)
    cmd = "cat log"
    _, stdout, stderr = ssh_client.exec_command(cmd)
    logs = stdout.readlines()
    try:
        if logs:
            result["server.lantency_p50"] = format_latency(
                logs[0].split()[0], "ms"
            )
            result["server.lantency_p90"] = format_latency(
                logs[1].split()[0], "ms"
            )
            result["server.rps"] = logs[2].split()[0]
        err = stderr.readlines()
        if err:
            log.error(f"cat log err :{err}")
            assert False
    except Exception as e:
        log.error(f"no found log :{e}")
        assert False
    return result

def reload_telegraf_conf(vm_ip, ssh_pool: SSHPool=ssh_pool_default):
    ssh_client = ssh_pool.get(vm_ip)
    _, stdout, stderr = ssh_client.exec_command("systemctl restart telegraf && systemctl status telegraf")
    output = stdout.read().decode()
    if "Active: active (running)" in output:
        log.info(f"deepflow agent restarted successfully and is running")
        return True
    else:
        log.error(
            f"deepflow-agent restart failed, err: {stderr.read().decode()}"
        )
        return False
    
def get_total_memory_Mbyte(vm_ip, ssh_pool: SSHPool=ssh_pool_default):
    ssh_client = ssh_pool.get(vm_ip)
    _, stdout, stderr = ssh_client.exec_command("free -b |awk '/Mem/{print $2}'")
    total_mem = stdout.read().decode().strip()
    err = stderr.read().decode()
    if err:
        log.error(f"get total memory Byte err: {err}")
    return int(total_mem)

def get_process_usage_by_telegraf(vm_ip, process_name_list, start_time, end_time):
    '''
    获取进程cpu/mem在一段时间内的90th的使用率
    return {'{process_name}_max_cpu_usage': 10.0, '{process_name}_max_mem_usage': 10.0}
    '''
    influx_db = InfulxDB(
        host=vm_ip,
        database=TELEGRAF_TABLE_NAME_IN_INFLUX,
    )
    procstat_data = {}
    # memory unit Mb
    total_memory = get_total_memory_Mbyte(vm_ip)
    for process_name in process_name_list:
        procstat = influx_db.get_procstat_result(process_name, start_time, end_time)
        # 内存百分比转换为Mb
        if "agent" in process_name:
            key = "agent"
        else:
            key = process_name.replace("-", "_")
        procstat_data[f"{key}.max_cpu"] = "{:.2f}%".format(procstat["max_cpu_usage"]) 
        procstat_data[f"{key}.max_mem"] = "{:.2f}Mb".format(float(procstat["max_mem_usage"]) * total_memory / 100)
    return procstat_data


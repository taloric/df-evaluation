from influxdb import InfluxDBClient

class InfulxDB:
    def __init__(self, host="127.0.0.1", port=8086, user="root", password="", database=""):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.client = InfluxDBClient(
            self.host, self.port, self.user, 
            self.password, self.database,
        )

    def get_procstat_result(self, process_name, start_time, end_time):
        '''获取特定进程cpu/mem在一段时间内的90th的使用率
        return {'max_cpu_usage': 10.0, 'max_mem_usage': 10.0}
        '''
        #time unit conversion s -> ns
        start_time = start_time * 1000000000
        end_time = end_time * 1000000000
        filter = f"pattern = '{process_name}'"
        sql = f"SELECT percentile(sum_cpu_usage, 90) AS max_cpu_usage, percentile(sum_memory_usage, 90) AS max_mem_usage \
                FROM (SELECT sum(cpu_usage) as sum_cpu_usage, sum(memory_usage) as sum_memory_usage FROM procstat \
                WHERE {filter} AND time >= {start_time} AND time <= {end_time} GROUP BY time(10s))"
        result = self.client.query(sql)
        procstat = list(result.get_points())
        return procstat[0]




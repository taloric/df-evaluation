## 1. Evaluation 功能
- 接收页面请求参数，包含测试例名称（测试场景）、待测agent类型等参数
- 根据场景搭建测试环境并执行测试例
- 收集环境、业务、agent的各项资源消耗以及服务指标
- 整理结果并输出
## 2. 软件架构
evaluation主要由evaluation进程和runner进程构成。evaluation进程主要负责webapi的接收、runner的调度、测试结果的整合输出。runner进程主要负责测试用例的执行，根据参数初始化测试环境，执行指定测试用例，保存测试结果。
![alt text](image.png)
## 3. 调用流程
web发送测试请求到Api-Server，Server将发送给Manager，Manage创建Runner子进程执行用例，测试执行完后Manager整合结果向外输出。
![alt text](image-1.png)
## 4. 代码框架
### 1. manager
调度进程
- 测试runner的创建
- 测试状态的监控和日志输出
- 测试结果的汇总的输出
- 测试请求的接收，排队
### 2. Runner
测试例执行进程
#### 2.1 agent-tools
各类采集器的调度类，每种采集器的tools需实现以下功能接口
- 创建、删除
- 启动、停止
- 状态正常检查
- 性能规格限制（cpu mem ...）
- 各指标获取（cpu占用 内存占用 ...）
- 配置写入
#### 2.2 cases
测试例的具体流程，实现以下场景：
- 极端高性能的业务场景（nginx-default-page）下部署agent前后性能表现
- 典型云原生微服务场景（istio-bookinfo-demo）下部署agent前后性能表现
- ...
#### 2.3 platform-tools
- Platform sdk base，每种云平台需实现该基类接口
  - 创建、删除虚拟机
  - 启动、停止虚拟机
  - 获取ip
  - 获取状态
- Aliyun sdk
### 3. Api-server
Http server 用于接收页面请求3
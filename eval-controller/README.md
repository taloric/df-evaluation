# Api Documentation

## Resource: auto-test

### POST /v1/evaluation/auto-test

#### args 
type: json
| name | type | required | description |
|------|------|----------|-------------|
| case_name | string | true | 测试例名称 |
| process_num | int | false | 测试例并发数 |

ps:
 - case_name的值需要从api `/v1/evaluation/dictionary/case`获取

example:
```
request:

curl -XPOST "http://127.0.0.1:10083/v1/evaluation/auto-test" -H "Content-Type: application/json" -d '{"case_name":"performance_analysis_nginx_http","process_num":1}'

reponse:

{
  "OPT_STATUS": "SUCCESS",
  "WAIT_CALLBACK": false,
  "TASK": null,
  "DESCRIPTION": "",
  "TYPE": "CaseRecord",
  "DATA": [
    {
      "ID": 6,
      "UUID": "be3fb069-b69a-4df6-b513-3c7cf24eb991",
      "CASE_NAME": "performance_analysis_nginx_http",
      ...
    }
  ]
}
```  

### GET /v1/evaluation/auto-test

#### args 
type: params
| name | type | required | description |
|------|------|----------|-------------|
| uuid | string | flase | 测试例uuid |

ps：
 - uuid不填时获取所有测试例

#### response
type: json
```
{
  "UUID": case_uuid,
  "CASE_NAME": case_name,
  "STATUS": case状态，具体含义调用api `/v1/evaluation/dictionary/case_status`获取
}
```

example:
```
request:

curl -XGET "http://127.0.0.1:10083/v1/evaluation/auto-test?uuid=be3fb069-b69a-4df6-b513-3c7cf24eb991"

reponse:

{
  "OPT_STATUS": "SUCCESS",
  "WAIT_CALLBACK": false,
  "TASK": null,
  "DESCRIPTION": "",
  "TYPE": "CaseRecord",
  "DATA": [
    {
      "ID": 6,
      "UUID": "be3fb069-b69a-4df6-b513-3c7cf24eb991",
      "CASE_NAME": "performance_analysis_nginx_http",
      "CASE_PARAMS": "",
      "USER": null,
      "RUNNER_COMMIT_ID": null,
      "RUNNER_IMAGE_TAG": null,
      "STATUS": 11,
      "DELETED": 0,
      "CREATED_AT": "2024-05-11 14:38:01"
    },
    ...
  ]
}
```

### PATCH /v1/evaluation/auto-test

#### args 
type: json
| name | type | required | description |
|------|------|----------|-------------|
| uuids | []string | true | 测试例uuid列表 |
| status | int | true | 需要修改的状态 |

ps:
 - status支持的值需调用api `/v1/evaluation/dictionary/case_status_support_update`获取， 2.暂停 3.取消 4.恢复

example:
```
request:

curl -XPATCH "http://127.0.0.1:10083/v1/evaluation/auto-test" -H "Content-Type: application/json" -d '{"uuids":["be3fb069-b69a-4df6-b513-3c7cf24eb991"],"status":2}'

reponse:

{
  "OPT_STATUS": "SUCCESS",
  "WAIT_CALLBACK": false,
  "TASK": null,
  "DESCRIPTION": "",
  "TYPE": "CaseRecord",
  "DATA": [
    {
      "ID": 6,
      "UUID": "be3fb069-b69a-4df6-b513-3c7cf24eb991",
      "CASE_NAME": "performance_analysis_nginx_http",
      ...
    }
  ]
}
```  

### DELETE /v1/evaluation/auto-test

#### args 
type: json
| name | type | required | description |
|------|------|----------|-------------|
| uuid | string | true | 测试例uuid |


## Resource: result

### GET /v1/evaluation/result/log
#### args 
type: params
| name | type | required | description |
|------|------|----------|-------------|
| uuid | string | true | 测试例uuid |
| type | int | true | 输出类型 |
| line_index | int | false | 指定行数位置开始读取,不传则从1开始 |
| line_size | int | false | 读取行数，不传则读取全部 |

ps：
 - type目前支持传 1.raw_log

#### reponse

```
{
  "uuid" :
  "logs" : [
    "",
    "",
    ""
  ],
  "line_index": 开始读取的行数
  "line_size": 返回的行数
  "line_count": 当前日志总行数
}
```

example:
```
request:

curl -XGET "http://127.0.0.1:10083/v1/evaluation/result/log?uuid=test213&type=1&line_index=2&line_size=3"

response:

{
  "OPT_STATUS": "SUCCESS",
  "WAIT_CALLBACK": false,
  "TASK": null,
  "DESCRIPTION": "",
  "TYPE": "dict",
  "DATA": {
    "uuid": "test213",
    "logs": [
      "qewqeqweq",
      "e21edwsads"
    ],
    "line_index": 2, # 开始读取的行数
    "line_size": 2, # 返回的行数
    "line_count": 3 # 总行数
  }
}
```

### GET /v1/evaluation/result/performance
#### args 
type: params
| name | type | required | description |
|------|------|----------|-------------|
| uuid | string | true | 测试例uuid |
| type | int | true | 输出类型 |

ps：
 - type目前支持传 2.md

#### response：
type: json
```
[
  ["filename1", "md string"],
  ["filename2", "md string"],
  ...
]
```

example:
```
request:

curl -XGET "http://127.0.0.1:10083/v1/evaluation/result/performance?uuid=4a4eb371-6a40-420b-bd42-b6fd30c1f5b7&type=2" |jq .


response:

{
  "OPT_STATUS": "SUCCESS",
  "WAIT_CALLBACK": false,
  "TASK": null,
  "DESCRIPTION": "",
  "TYPE": "list",
  "DATA": [
    [
      "24051016-0553a94-agnet-perfromance-report_performance_protocol.md",
      "# 开源采集器性能测试报告 - latest\n## 摘要\n本文档为开源采集器（deepflow-agent）的性能测试报告，将评估 Agent 在不同应用协议下的流量，分析其自身资源消耗。测试版本为 latest，测试完成时间为2024-05-10 16:34:00。\n\n## 测试环境\n环境信息：...
    ]
  ]
}
```

## Resource: dictionary
### GET /v1/evaluation/dictionary/case
#### args 
type: params
| name | type | required | description |
|------|------|----------|-------------|

#### response：
type: json
```
[
  ["casename1", "case_path1", "case_description1"],
  ["casename2", "case_path2", "case_description2"],
  ...
]
```

example:
```
request:

curl -XGET "http://127.0.0.1:10083/v1/evaluation/dictionary/case" |jq .

response:

{
  "OPT_STATUS": "SUCCESS",
  "WAIT_CALLBACK": false,
  "TASK": null,
  "DESCRIPTION": "",
  "TYPE": "list",
  "DATA": [
    [
      "performance_analysis_nginx_http",
      "performance_analysis/test_performance_analysis_nginx_http.py",
      "性能分析-极端高性能场景(nginx)"
    ]
  ]
}

```

### GET /v1/evaluation/dictionary/case_status_support_update
#### args
type: params
| name | type | required | description |
|------|------|----------|-------------|
#### response：
type: json
```
[
  [修改的case状态，状态名称，可供修改的状态列表]
]
```

example:
```
request:

curl -XGET "http://127.0.0.1:10083/v1/evaluation/dictionary/case_status_support_update" |jq .


response:

{
  "OPT_STATUS": "SUCCESS",
  "WAIT_CALLBACK": false,
  "TASK": null,
  "DESCRIPTION": "",
  "TYPE": "list",
  "DATA": [
    [2, "pause", [1]], # 只能在状态为1时修改状态为2
    [3, "cancel", [1, 2]], 只能在状态为1或2时修改状态为3
    [4, "resume", [2]]
  ]
}

```

### GET /v1/evaluation/dictionary/case_status
#### args
type: params
| name | type | required | description |
|------|------|----------|-------------|
#### response：
type: json
```
[
  [状态int, 状态名称],
  ...
]
```

example:
```
request:

curl -XGET "http://127.0.0.1:10083/v1/evaluation/dictionary/case_status" |jq .

response:

{
  "OPT_STATUS": "SUCCESS",
  "WAIT_CALLBACK": false,
  "TASK": null,
  "DESCRIPTION": "",
  "TYPE": "list",
  "DATA": [
    [
      0,
      "Init"
    ],
    [
      11,
      "Starting"
    ],
    [
      1,
      "Running"
    ],
    [
      12,
      "Pending"
    ],
    [
      2,
      "Paused"
    ],
    [
      21,
      "Pausing"
    ],
    [
      3,
      "Finished"
    ],
    [
      31,
      "Stopping"
    ],
    [
      4,
      "Error"
    ]
  ]
}

```
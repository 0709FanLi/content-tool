# 火山引擎即梦图生图 API 文档 (jimeng_t2i_v40)

## 节点信息

### 接口地址
- **Base URL**: `https://visual.volcengineapi.com`
- **API Version**: `2022-08-31`

### 使用方式
使用火山引擎视觉智能 API，需要配置 AccessKey 和 SecretKey 进行 HMAC-SHA256 签名认证。

---

## 环境变量配置

### 火山引擎AccessKey（必须配置）
```bash
VOLC_ACCESS_KEY_ID=your_access_key_id
VOLC_SECRET_ACCESS_KEY=your_secret_access_key
VOLC_BASE_URL=https://visual.volcengineapi.com  # 可选，默认值
```

---

## 接口列表

### 1. 提交图片生成任务

**接口地址:** `/`

**请求方式:** POST

**查询参数:**
- `Action`: `CVSync2AsyncSubmitTask`
- `Version`: `2022-08-31`

**请求头 Headers:**
```
Content-Type: application/json
Host: visual.volcengineapi.com
X-Date: 20231114T120000Z
X-Content-Sha256: <payload_hash>
Authorization: HMAC-SHA256 Credential=<access_key_id>/<credential_scope>, SignedHeaders=content-type;host;x-content-sha256;x-date, Signature=<signature>
```

**请求参数 (JSON):**
```json
{
  "req_key": "jimeng_t2i_v40",
  "prompt": "提示词，最长800字符",
  "force_single": true,
  "width": 1024,
  "height": 1024,
  "image_urls": [
    "https://example.com/reference1.jpg",
    "https://example.com/reference2.jpg"
  ]
}
```

**参数说明:**

| 参数名 | 类型 | 必填 | 示例 | 描述 |
|--------|------|------|------|------|
| req_key | string | 是 | `"jimeng_t2i_v40"` | 请求类型，固定值 |
| prompt | string | 是 | `"一只可爱的猫咪在草地上玩耍"` | 提示词，最长800字符 |
| force_single | boolean | 是 | `true` | 强制单图输出 |
| width | number | 否 | `1024` | 图片宽度（像素） |
| height | number | 否 | `1024` | 图片高度（像素） |
| image_urls | array | 否 | `["https://example.com/ref1.jpg"]` | 参考图URL列表，支持0-6张 |

**响应结果:**
```json
{
  "code": 10000,
  "message": "success",
  "data": {
    "task_id": "7392616336519610409"
  }
}
```

**响应参数说明:**

- **code**
  - 类型: number
  - 示例: 10000
  - 描述: 状态码，10000 表示成功

- **message**
  - 类型: string
  - 示例: "success"
  - 描述: 状态信息

- **data.task_id**
  - 类型: string
  - 示例: "7392616336519610409"
  - 描述: 任务ID，用于后续查询结果

---

### 2. 查询任务结果

**接口地址:** `/`

**请求方式:** POST

**查询参数:**
- `Action`: `CVSync2AsyncGetResult`
- `Version`: `2022-08-31`

**请求头 Headers:**
```
Content-Type: application/json
Host: visual.volcengineapi.com
X-Date: 20231114T120000Z
X-Content-Sha256: <payload_hash>
Authorization: HMAC-SHA256 Credential=<access_key_id>/<credential_scope>, SignedHeaders=content-type;host;x-content-sha256;x-date, Signature=<signature>
```

**请求参数 (JSON):**
```json
{
  "req_key": "jimeng_t2i_v40",
  "task_id": "<任务提交接口返回task_id>",
  "req_json": "{\"return_url\": true}"
}
```

**参数说明:**

| 参数名 | 类型 | 必填 | 示例 | 描述 |
|--------|------|------|------|------|
| req_key | string | 是 | `"jimeng_t2i_v40"` | 请求类型，固定值 |
| task_id | string | 是 | `"7392616336519610409"` | 任务ID，此字段的取值为提交任务接口的返回 |
| req_json | string | 是 | `"{\"return_url\": true}"` | JSON字符串，设置返回URL |

**响应结果:**

**任务进行中:**
```json
{
  "code": 10000,
  "message": "success",
  "data": {
    "status": "in_queue",
    "task_id": "7392616336519610409"
  }
}
```

**任务完成:**
```json
{
  "code": 10000,
  "message": "success",
  "data": {
    "status": "done",
    "task_id": "7392616336519610409",
    "image_urls": [
      "https://example.com/generated_image.jpg"
    ]
  }
}
```

**响应参数说明:**

- **code**
  - 类型: number
  - 示例: 10000
  - 描述: 状态码，10000 表示成功

- **data.status**
  - 类型: string
  - 示例: "done"
  - 描述: 任务状态
    - `"in_queue"`: 任务排队中
    - `"generating"`: 生成中
    - `"done"`: 已完成
    - `"not_found"`: 任务未找到
    - `"expired"`: 任务已过期

- **data.image_urls**
  - 类型: array
  - 示例: `["https://example.com/generated_image.jpg"]`
  - 描述: 生成的图片URL列表（任务完成时返回）

---

## 认证说明

### HMAC-SHA256 签名算法

火山引擎 API 使用 HMAC-SHA256 签名算法进行认证。

**签名步骤:**

1. **构建 CanonicalRequest**
   ```
   POST
   /
   Action=CVSync2AsyncSubmitTask&Version=2022-08-31
   content-type:application/json
   host:visual.volcengineapi.com
   x-content-sha256:<payload_hash>
   x-date:20231114T120000Z
   
   content-type;host;x-content-sha256;x-date
   <hashed_payload>
   ```

2. **构建 StringToSign**
   ```
   HMAC-SHA256
   20231114T120000Z
   20231114/cn-north-1/cv/request
   <hashed_canonical_request>
   ```

3. **计算签名**
   - 使用 SecretKey 和日期计算 k_date
   - 使用 k_date 和区域计算 k_region
   - 使用 k_region 和服务名计算 k_service
   - 使用 k_service 和 "request" 计算 k_signing
   - 使用 k_signing 和 StringToSign 计算最终签名

4. **构建 Authorization Header**
   ```
   Authorization: HMAC-SHA256 Credential=<access_key_id>/<credential_scope>, SignedHeaders=content-type;host;x-content-sha256;x-date, Signature=<signature>
   ```

---

## 使用示例

### Python 示例

```python
import os
import asyncio
from src.services.volc_jimeng_service import volc_jimeng_service

# 设置环境变量
os.environ["VOLC_ACCESS_KEY_ID"] = "your_access_key_id"
os.environ["VOLC_SECRET_ACCESS_KEY"] = "your_secret_access_key"

# 生成图片
async def generate_image():
    try:
        image_url = await volc_jimeng_service.generate_image(
            prompt="一只可爱的猫咪在草地上玩耍",
            size="1024x1024",
            reference_image_urls=["https://example.com/reference.jpg"]
        )
        print(f"生成的图片URL: {image_url}")
    except Exception as e:
        print(f"生成失败: {e}")

# 运行
asyncio.run(generate_image())
```

---

## 注意事项

1. **任务轮询**: 提交任务后需要轮询查询结果，建议每2秒查询一次，最多查询30次
2. **超时处理**: 如果60秒内任务未完成，建议重新提交任务
3. **参考图限制**: 参考图最多支持6张
4. **提示词长度**: 提示词最长800字符
5. **图片尺寸**: 支持自定义宽度和高度（像素）
6. **错误处理**: 
   - `火山即梦未返回task_id`: 响应格式异常
   - `火山即梦任务未找到`: task_id无效或已过期
   - `火山即梦任务已过期`: 任务超时
   - `火山即梦未返回图片`: 生成失败

---

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 10000 | 成功 |
| 其他 | 参考火山引擎官方文档 |

---

## 相关资源

- 火山引擎视觉智能 API 官方文档: https://www.volcengine.com/docs/6369/67268
- 公共参数说明: https://www.volcengine.com/docs/6369/67268


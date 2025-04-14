# API 文档

## 基础信息

- 基础URL: `http://localhost:5000`
- 所有请求都需要包含 `Content-Type: application/json` 头
- 认证使用 Session Cookie

## 认证接口

### 登录

```http
POST /auth/login
```

请求体：
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

响应：
```json
{
    "success": true,
    "user": {
        "id": 1,
        "email": "user@example.com",
        "role": "student"
    }
}
```

### 注销

```http
POST /auth/logout
```

响应：
```json
{
    "success": true
}
```

## 项目接口

### 获取项目列表

```http
GET /api/projects
```

查询参数：
- `page`: 页码（默认：1）
- `per_page`: 每页数量（默认：10）
- `field`: 项目领域过滤
- `search`: 搜索关键词

响应：
```json
{
    "projects": [
        {
            "id": 1,
            "title": "医疗影像AI分析",
            "description": "使用深度学习进行医疗影像分析",
            "field": "医疗健康",
            "teacher_email": "teacher@example.com",
            "interested_count": 3
        }
    ],
    "total": 100,
    "page": 1,
    "per_page": 10
}
```

### 创建项目

```http
POST /api/projects
```

请求体：
```json
{
    "title": "医疗影像AI分析",
    "description": "使用深度学习进行医疗影像分析",
    "field": "医疗健康"
}
```

响应：
```json
{
    "success": true,
    "project": {
        "id": 1,
        "title": "医疗影像AI分析",
        "description": "使用深度学习进行医疗影像分析",
        "field": "医疗健康",
        "teacher_email": "teacher@example.com"
    }
}
```

## AI 对话接口

### 发送消息

```http
POST /api/chat
```

请求体：
```json
{
    "message": "我想做关于医疗AI的项目",
    "session_id": "abc123"
}
```

响应：
```json
{
    "type": "project_matches",
    "projects": [
        {
            "id": 1,
            "title": "医疗影像AI分析",
            "description": "使用深度学习进行医疗影像分析",
            "field": "医疗健康",
            "matching_score": 0.95,
            "reasoning": "该项目完全符合您对医疗AI的兴趣"
        }
    ]
}
```

## 项目选择接口

### 表达兴趣

```http
POST /api/interest/{project_id}
```

响应：
```json
{
    "success": true,
    "message": "已成功表达对项目的兴趣"
}
```

### 取消兴趣

```http
DELETE /api/interest/{project_id}
```

响应：
```json
{
    "success": true,
    "message": "已成功取消对项目的兴趣"
}
```

## 错误处理

所有接口在发生错误时都会返回相应的 HTTP 状态码和错误信息：

```json
{
    "error": true,
    "message": "错误描述",
    "code": "ERROR_CODE"
}
```

常见状态码：
- 400: 请求参数错误
- 401: 未认证
- 403: 无权限
- 404: 资源不存在
- 500: 服务器内部错误

## 速率限制

- 普通接口：60次/分钟
- AI对话接口：10次/分钟

超过限制将返回 429 状态码：
```json
{
    "error": true,
    "message": "请求过于频繁，请稍后再试",
    "code": "RATE_LIMIT_EXCEEDED"
}
```

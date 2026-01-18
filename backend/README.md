# SmokeSignal Analytics Backend

后端API服务，用于买家数据分析、CRM和AI画像生成。

## 📋 功能特性

- ✅ 从MySQL数据库读取订单和聊天数据
- ✅ 自动计算买家标签（VIP等级、折扣敏感度、流失风险等）
- ✅ 集成智谱GLM-4.7进行AI买家画像分析
- ✅ RESTful API接口
- ✅ 自动生成API文档

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

**数据库配置**（已与chat-history-crawler共享）：
- 数据库配置从用户根目录的 `~/database_config.json` 读取
- 无需在 `.env` 中配置数据库信息

**其他配置**：
- `.env` 文件已包含智谱API密钥，无需修改
- 如需修改API端口等，可编辑 `.env` 文件

### 3. 启动服务

```bash
python -m backend.main
```

或使用 uvicorn：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

服务将在 `http://localhost:8000` 启动

### 4. 访问API文档

打开浏览器访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📊 API接口

### 核心接口

#### 1. 获取所有买家列表
```
GET /api/buyers
```

#### 2. 获取买家完整画像
```
GET /api/buyers/{user_nick}
```

参数：
- `include_ai` (optional): 是否包含AI分析，默认false

#### 3. 获取买家订单历史
```
GET /api/buyers/{user_nick}/orders?limit=50
```

#### 4. 获取买家聊天记录
```
GET /api/buyers/{user_nick}/chats?limit=100
```

#### 5. 触发AI分析
```
POST /api/buyers/{user_nick}/ai-analysis
```

#### 6. 获取Dashboard指标
```
GET /api/dashboard/metrics
```

#### 7. 获取每日统计
```
GET /api/dashboard/daily-stats?days=30
```

#### 8. 获取需要关注的客户
```
GET /api/dashboard/actionable-customers
```

## 🏷️ 标签体系

### VIP等级（基于rolling 24个月netsales）
- **Non-VIP**: < 30,000元
- **V0**: 30,000 - 49,999元
- **V1**: 50,000 - 149,999元
- **V2**: 150,000 - 449,999元
- **V3**: >= 450,000元

### 折扣敏感度
- **高度敏感**: 折扣品占比 >= 70%
- **中度敏感**: 折扣品占比 >= 40%
- **低度敏感**: 折扣品占比 < 40%

### 流失风险
- **流失客户**: 2年无购买 AND 6个月无咨询
- **流失预警**: 6个月无购买 AND 30天无咨询

### 其他标签
- 折扣猎手
- 高频/中频/低频买家
- 成长/成熟客户
- 高价值客户
- 斗客/配件客（基于品类偏好）

## 📁 项目结构

```
backend/
├── main.py                  # FastAPI应用入口
├── config.py                # 配置管理
├── requirements.txt         # Python依赖
├── .env                     # 环境变量（需自行创建）
├── .env.example             # 环境变量示例
├── analytics/              # 数据分析模块
│   ├── __init__.py
│   ├── tag_calculator.py   # 标签计算逻辑
│   └── buyer_analyzer.py   # 买家分析主类
├── database/               # 数据库模块
│   ├── __init__.py
│   ├── connection.py       # 数据库连接
│   └── queries.py          # SQL查询
├── ai/                     # AI模块
│   ├── __init__.py
│   └── zhipu_client.py     # 智谱AI客户端
└── api/                    # API路由
    ├── __init__.py
    └── routes.py           # API端点定义
```

## 🔧 开发指南

### 添加新的标签计算逻辑

在 `analytics/tag_calculator.py` 中添加新的计算方法：

```python
@staticmethod
def calculate_your_new_tag(metrics) -> Dict[str, Any]:
    """计算新标签"""
    # Your logic here
    return {"tag": "value"}
```

### 添加新的API端点

在 `api/routes.py` 中添加新路由：

```python
@router.get("/your-new-endpoint")
async def your_new_endpoint():
    """新的API端点"""
    # Your logic here
    return result
```

## 🧪 测试API

使用curl测试：

```bash
# 健康检查
curl http://localhost:8000/

# 获取所有买家
curl http://localhost:8000/api/buyers

# 获取买家画像（不含AI）
curl http://localhost:8000/api/buyers/崔华伟1984

# 获取买家画像（含AI分析）
curl http://localhost:8000/api/buyers/崔华伟1984?include_ai=true

# 触发AI分析
curl -X POST http://localhost:8000/api/buyers/崔华伟1984/ai-analysis
```

## ⚠️ 注意事项

1. **数据库连接**: 确保用户根目录下存在 `~/database_config.json` 文件
2. **智谱API Key**: 已预配置，但请确认额度充足
3. **AI分析耗时**: AI分析需要几秒时间，建议异步调用或缓存结果
4. **字符编码**: 确保数据库使用 `utf8mb4` 编码以支持中文
5. **退款金额NULL处理**: SQL中已使用 `IFNULL(退款金额, 0)` 处理NULL值

## 🚀 部署建议

### 开发环境
```bash
uvicorn backend.main:app --reload
```

### 生产环境
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 使用Docker（待实现）
```bash
docker build -t smokesignal-backend .
docker run -p 8000:8000 --env-file .env smokesignal-backend
```

## 📞 故障排查

### 问题1: 数据库连接失败
- 检查 `~/database_config.json` 文件是否存在
- 确认配置文件中的数据库信息正确
- 确认MySQL服务运行中
- 检查防火墙设置

### 问题2: 智谱API调用失败
- 确认API key正确
- 检查API额度
- 查看错误日志

### 问题3: 中文乱码
- 确保数据库表使用 `utf8mb4` 编码
- 检查连接字符串中的 `charset=utf8mb4`

## 📝 更新日志

### v1.0.0 (2025-01-16)
- ✅ 初始版本
- ✅ 数据库集成
- ✅ 标签计算系统
- ✅ 智谱AI集成
- ✅ RESTful API

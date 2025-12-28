# Flask Visitor Tracker

一个基于 Flask 的访客追踪系统，可以与 WordPress 网站集成，收集访客信息、统计数据和 HTTP 访问日志。

## 功能特性

- 页面浏览追踪
- 点击事件追踪
- 滚动深度追踪
- 表单交互追踪
- 设备信息收集（浏览器、操作系统、设备类型）
- 实时访问日志
- 统计分析 API
- 数据自动清理
- IP 地址匿名化

## 项目结构

```
flask-visitor-tracker/
├── app.py                    # Flask 主应用入口
├── config.json               # 配置文件
├── requirements.txt          # Python 依赖
├── tracker/
│   ├── __init__.py
│   ├── routes.py            # API 路由
│   ├── services.py          # 业务逻辑
│   └── utils.py             # 工具函数
├── static/
│   └── tracker.js           # WordPress 引用的 JS 文件
└── data/
    ├── visits.json          # 访问记录
    ├── events.json          # 事件记录
    └── http_access.log      # HTTP 访问日志
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 config.json

编辑 `config.json`，修改以下配置：

```json
{
  "app": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false
  },
  "domains": {
    "allowed": ["your-wordpress-domain.com"],
    "cors_origins": ["https://your-wordpress-domain.com"]
  },
  "tracking": {
    "anonymize_ip": true,
    "data_retention_days": 90
  }
}
```

### 3. 运行应用

```bash
python app.py
```

## WordPress 集成

### 方法一：通过 functions.php

在主题的 `functions.php` 中添加：

```php
function enqueue_tracker_scripts() {
    wp_enqueue_script(
        'visitor-tracker',
        'https://your-flask-app.pythonanywhere.com/tracker.js',
        array(),
        '1.0.0',
        true
    );

    wp_add_inline_script('visitor-tracker', '
        window.addEventListener("load", function() {
            VisitorTracker.init("https://your-flask-app.pythonanywhere.com");
        });
    ');
}
add_action('wp_enqueue_scripts', 'enqueue_tracker_scripts');
```

### 方法二：通过插件

创建 WordPress 插件 `wp-content/plugins/flask-tracker/flask-tracker.php`：

```php
<?php
/*
Plugin Name: Flask Visitor Tracker
Description: 集成 Flask 访客追踪系统
Version: 1.0.0
*/

function enqueue_tracker_scripts() {
    wp_enqueue_script(
        'flask-tracker',
        'https://your-flask-app.pythonanywhere.com/tracker.js',
        array(),
        '1.0.0',
        true
    );

    wp_add_inline_script('flask-tracker', '
        document.addEventListener("DOMContentLoaded", function() {
            VisitorTracker.init("https://your-flask-app.pythonanywhere.com");
        });
    ');
}
add_action('wp_enqueue_scripts', 'enqueue_tracker_scripts');
?>
```

### 方法三：直接嵌入

在主题的 `header.php` 或 `footer.php` 中添加：

```html
<script src="https://your-flask-app.pythonanywhere.com/tracker.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        VisitorTracker.init('https://your-flask-app.pythonanywhere.com');
    });
</script>
```

## API 接口

### 记录访问

```bash
POST /api/tracker/visit
Content-Type: application/json

{
    "pageUrl": "https://example.com/page",
    "referrer": "https://google.com",
    "screenResolution": "1920x1080",
    "language": "zh-CN",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### 记录事件

```bash
POST /api/tracker/event
Content-Type: application/json

{
    "eventType": "click",
    "eventData": {"tag": "button", "text": "Submit"},
    "visitId": "visit_abc123",
    "elementSelector": "#submit-btn"
}
```

### 批量记录事件

```bash
POST /api/tracker/events
Content-Type: application/json

{
    "events": [
        {"eventType": "click", "eventData": {...}},
        {"eventType": "scroll_depth", "eventData": {...}}
    ]
}
```

### 获取统计数据

```bash
GET /api/tracker/stats?metric=overview&startDate=2024-01-01&endDate=2024-01-31
```

支持的 metric 值：
- `overview` - 总览统计
- `pageviews` - 页面浏览量
- `visitors` - 访客统计
- `sources` - 来源统计
- `devices` - 设备统计
- `browsers` - 浏览器统计
- `timeline` - 时间线统计

### 获取访问日志

```bash
GET /api/tracker/logs?limit=100
```

### 健康检查

```bash
GET /api/tracker/health
```

## PythonAnywhere 部署

### 1. 上传代码

将项目上传到 GitHub，然后在 PythonAnywhere 的 Bash 控制台克隆：

```bash
git clone https://github.com/your-username/flask-visitor-tracker.git
cd flask-visitor-tracker
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 WSGI

在 PythonAnywhere 的 "Web" 标签页，编辑 WSGI 配置文件：

```python
import sys
import os

project_home = '/home/your-username/flask-visitor-tracker'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from app import app as application
```

### 4. 配置静态文件

在 PythonAnywhere 的 "Static Files" 表格中添加：

| URL | Directory |
|-----|-----------|
| /tracker.js | /home/your-username/flask-visitor-tracker/static/tracker.js |

### 5. 重载应用

点击 "Reload" 按钮。

### 6. 配置定时任务（可选）

设置每天自动清理旧数据：

```bash
crontab -e
# 添加：
0 3 * * * cd /home/your-username/flask-visitor-tracker && python -c "from app import create_app; app = create_app(); app.test_client().post('/api/tracker/cleanup')"
```

## 数据存储

- **visits.json**: 存储所有访问记录
- **events.json**: 存储所有事件记录
- **http_access.log**: 存储 HTTP 访问日志

所有数据存储在 `data/` 目录下，使用 JSON 格式。

## 配置说明

### config.json 完整配置

```json
{
  "app": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false,
    "secret_key": "your-secret-key"
  },
  "domains": {
    "allowed": ["your-domain.com"],
    "cors_origins": ["https://your-domain.com"]
  },
  "tracking": {
    "session_timeout_minutes": 30,
    "max_events_per_session": 100,
    "data_retention_days": 90,
    "anonymize_ip": true
  },
  "features": {
    "track_pageviews": true,
    "track_clicks": true,
    "track_scroll": true,
    "track_forms": true
  },
  "logging": {
    "enable_http_logging": true,
    "log_file": "data/http_access.log",
    "max_log_lines": 10000
  }
}
```

## 安全建议

1. 在生产环境中修改 `secret_key`
2. 启用 `anonymize_ip` 保护用户隐私
3. 限制 CORS origins 到你的 WordPress 域名
4. 定期清理过期数据
5. 使用 HTTPS 传输数据

## 统计指标

系统收集以下统计指标：

- **页面浏览量 (Pageviews)**: 页面被访问的总次数
- **独立访客 (Unique Visitors)**: 不同的访客数量
- **来源分析 (Sources)**: 访客来自哪些网站
- **设备统计 (Devices)**: 桌面/移动/平板设备分布
- **浏览器统计 (Browsers)**: Chrome/Firefox/Safari 等分布
- **时间线 (Timeline)**: 按日期的访问趋势

## JavaScript API

```javascript
// 初始化追踪器
VisitorTracker.init('https://your-api-endpoint.com');

// 手动追踪事件
VisitorTracker.manualTrack('custom_event', {key: 'value'});

// 获取会话信息
const sessionInfo = VisitorTracker.getSessionInfo();

// 发送心跳
VisitorTracker.ping();
```

## 许可证

MIT License

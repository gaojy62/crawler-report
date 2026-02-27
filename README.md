# Crawler Report System

自动采集财经新闻、通过 AI 汇总整理生成报告并推送的系统。

## 功能

- RSS 订阅爬取
- Twitter 账号爬取
- AI 相关性打分筛选
- Markdown 报告生成
- 自动推送通知

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置数据源
cp config/sources.yaml.example config/sources.yaml

# 运行
python src/main.py
```

## 配置

在 `config/sources.yaml` 中配置：
- RSS 订阅源
- Twitter 账号
- AI 打分参数

## 部署

使用 GitHub Actions 定时运行，每天自动生成报告并推送。

## 环境变量

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `WORKER_URL` | openclaw-push Worker 地址 |
| `PUSH_TOKEN` | 推送认证 Token |
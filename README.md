# StallSpan 市集摊档开间

沿街段一维 First-Fit 开间分配，挡柱不可被摊位跨越，输出分配图与放不下清单。

技术栈：Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vue 3 / TypeScript / Vite

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4700 |
| API | http://localhost:9700 |
| API 文档 | http://localhost:9700/docs |
| Postgres | localhost:5448 |

健康检查：`GET http://localhost:9700/api/health`

## 使用说明

1. 在「集日」「街段」确认开市日、可用宽度与相邻两摊的消防净距（米，0 表示可端点相接）。
2. 在「摊主」「挡柱」维护需求宽度与障碍位置。
3. 打开「分配图」执行一维开间分配：净距占用空档，图上相邻两摊的空隙米数与引擎占用一致。
4. 在「放不下」查看无法安置的摊位；拒因分两类互斥：净距不足 / 空档总长不够（含跨挡柱）。

> 改街段净距并保存后立即落库；随后「重新分配」按新净距现算，「放不下」读取时若发现缓存是改前口径会自动按新净距重算，不吃旧缓存。

## 开发与测试

```bash
docker compose exec api pytest -q
```

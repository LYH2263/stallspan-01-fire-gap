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

1. 在「集日」「街段」确认开市日与可用宽度。
2. 在「街段」登记摊间消防净距（米）：相邻两摊之间必须留出的最小净距，0 表示允许端点相接；保存后分配图与放不下清单即按新净距现算，不吃改前缓存。
3. 在「摊主」「挡柱」维护需求宽度与障碍位置。
4. 打开「分配图」执行一维开间分配：按优先序从左填空档，新摊起点至少离开前一摊终点一个净距；图上阴影空隙即引擎占用的净距，米数一致。
5. 在「放不下」查看无法安置的摊位，拒因互斥：「净距不足」与「空档总长不够（不跨越挡柱）」不会并成一句。

## 开发与测试

```bash
docker compose exec api pytest -q
```

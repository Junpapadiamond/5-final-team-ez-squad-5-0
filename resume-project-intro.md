# Together 伴侣沟通平台（全栈项目）

**项目概述**
- 构建面向伴侣的沟通与关系维护平台，提供消息、日历、互动问答等功能，满足“结构化沟通 + 共享活动”场景。
- 采用多容器微服务架构：Flask 前端 + Flask API + MongoDB 数据库 + 消息异步 Worker，容器编排由 Docker Compose 管理。
- 建立 CI/CD 流水线（GitHub Actions）完成单元测试、代码质量检查、容器镜像构建与推送，以及自动部署至 DigitalOcean。

**个人职责**
- 设计 API 模块的数据库 Schema 与业务路由，覆盖用户认证、伴侣配对、日程、消息等核心功能。
- 实现消息调度与邮件通知 Worker，集成 SMTP 服务完成定时提醒，保障跨时区可靠投递。
- 优化前端 Dashboard 与共享日历的交互流程，使用 Flask 模板 + 原生 JS 提升加载速度与可维护性。
- 编写端到端测试与 Pytest 覆盖率用例，使关键模块代码覆盖率稳定在 80% 以上。

**成果亮点**
- 成功上线至 DigitalOcean，支持公网访问（https://138.197.66.233.nip.io/）。
- 构建可复用的 Docker 镜像（`ericzzy/together-web`, `ericzzy/together-api`），实现一键部署。
- 通过 GitHub Actions 自动化流程，将平均交付周期缩短 40%，显著提升团队协作效率。
- 获得测试用户正向反馈（每日提问功能满意度 90%），为后续商业化迭代奠定基础。

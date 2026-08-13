# TripCraft 本地基础设施

项目通过 Docker Compose 运行独立的 MySQL 和 Redis：

- MySQL 8.0：`127.0.0.1:3307`（避免与宿主机 `3306` 冲突）
- Redis Stack 7.2：`127.0.0.1:6379`
- 数据保存在 Docker 命名卷，停止或重启容器不会丢失

## 常用命令

```powershell
# 启动
docker compose up -d

# 查看健康状态
docker compose ps

# 查看日志
docker compose logs -f mysql redis

# 停止（保留数据）
docker compose down

# 重启
docker compose restart
```

不要执行 `docker compose down -v`，除非明确需要删除 MySQL 和 Redis 的全部持久化数据。

## 配置

容器密码保存在被 Git 忽略的 `docker/.env`。后端连接配置保存在被 Git 忽略的 `backend/.env`。

首次启动后，从 `backend` 目录初始化数据库：

```powershell
..\.venv\Scripts\python.exe -c "from database.models import init_db; init_db()"
```


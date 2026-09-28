# Docker 数据盘迁移检查记录

日期：2026-09-28。

## 迁移结果

已通过 Docker Desktop 的 Settings → Resources → Advanced → Disk image location 完成迁移，并执行 Apply & restart。

- Docker 当前存储根目录：`E:\DockerData\DockerDesktopWSL`。
- 数据盘：`E:\DockerData\DockerDesktopWSL\disk\docker_data.vhdx`。
- WSL 系统盘：`E:\DockerData\DockerDesktopWSL\main\ext4.vhdx`。
- 设置中的 `CustomWslDistroDir` 与上述根目录一致。
- 原 C 盘目录中已无上述 VHDX 文件；本次移动释放约 7.2 GiB。完成检查时 C 盘空闲约 15.6 GiB，E 盘空闲约 225.6 GiB。

Docker Desktop 程序及少量设置、日志仍在 C 盘。本次迁移的是容器、镜像、数据卷所在的数据盘。

## 完整性与运行检查

| 检查项 | 结果 |
| --- | --- |
| 镜像 ID | 迁移前后 22 个，完全一致（包含构建中间镜像） |
| 容器 ID | 迁移前后 6 个，完全一致 |
| 数据卷名称 | 迁移前后 3 个，完全一致 |
| 容器文件系统 | 使用已有 Python 镜像，无网络运行临时容器；写入、读取、删除测试文件成功 |
| PostgreSQL | 原容器恢复，健康检查通过，仍挂载 `agentcode_postgres_data`；事务内创建临时表、写入与读取成功，已回滚 |
| Redis | 原容器恢复，健康检查通过，仍挂载 `agentcode_redis_data`；PING 返回 PONG |

迁移前后的 ID 清单保存在本地忽略提交的 `.build-context/migration-check/`。没有重置 Docker，也没有清空原有数据卷。

## 保留的备份

迁移前、Docker 停止时的备份：`E:\DockerData\migration-backup-20260928`。

- `docker_data.vhdx`：7,648,313,344 字节。
- 复制后与当时的源盘 SHA-256 一致：`85E766E7F7EA1230100731F35AE28FB131A5F35F827C917B6C442D37A3421998`。
- 同目录保留迁移前的 `settings-store.json`。

备份仍保留在 E 盘。它是迁移前的快照，不会随当前容器更新。恢复时应先停止 Docker；不要用旧备份覆盖正在使用的数据盘。

此前阻碍启动的临时运行目录已改名保留为 `C:\Users\32157\AppData\Local\Docker\run.migration-stale-20260928`；电脑重启后 Docker 正常启动。

## 项目环境边界

Docker 数据盘迁移成功后，项目的 PostgreSQL、Redis、MinIO、后端、worker 和前端均已完成构建并运行。数据库处于 `0015_knowledge_lifecycle`，已通过真实文件上传、DashScope 向量化、后台处理与删除清理验收。

按用户要求，删除了 `eloquent_taussig`、`sleepy_ishizaka`、`cranky_easley` 三个失败构建容器，以及独立验证数据库 `codeatlas-lifecycle-postgres` 和其匿名测试卷。本轮重新构建留下的三个失败容器也已精确删除。最终仅保留项目必需的六个容器；业务数据卷和迁移备份仍保留。

完整业务验收结果见 [知识库生命周期验收记录](knowledge-ingestion-acceptance-2026-09-28.md)。

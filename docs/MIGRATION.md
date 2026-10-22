# 仓库整合记录

## 最终结构

- 整合仓库：`dxw2544523082/big-market-fullstack-dxw`。
- 默认分支：`main`，含 `backend/`、`frontend/` 和统一配置/启动脚本。
- 原后端 20 个本地分支以 `backend-` 前缀保留。
- 原前端 3 个本地分支以 `frontend-` 前缀保留。
- 合计 24 个分支，包括整合主分支。原分支名中的中文保留。

采用 Git subtree 非 squash 合入，两套提交历史均可追溯。归档分支的文件布局仍是当时的独立项目布局；请从 `main` 运行整合项目。

## 安全与备份

1. 迁移前保存双方 `git bundle --all`，包含本地分支、远程跟踪 refs 与全部可达对象；另保存 GitHub mirror。
2. 源码压缩包包含未跟踪源码及 `.env.local` 等本地配置，不包含依赖、产物和运行日志。
3. 源码恢复后逐文件 SHA256 校验；bundle 恢复后 refs 对比与 `git fsck --full` 校验通过。
4. 历史中 3 个非通用口令仅在新整合副本中替换为占位符；原始哈希和敏感值不在文档中展示。git-filter-repo 的提交映射与原始版本保存在仓库之外。
5. 对 GitHub 的 Issues、PR、评论、Releases、Milestones、Labels、Deployments、Actions、Hooks 等元数据进行了备份。两个旧仓库均无 Issues、PR、Releases、Actions 或部署记录，不需要迁移附件。

## 旧仓库保留

按用户最新指示，以下两仓库**不删除、不强推、不改写**：

- https://github.com/dxw2544523082/big-market-dxw
- https://github.com/dxw2544523082/big-market-front-dxw

本地原项目目录同样保持不变。新整合仓库的安全修复不会自动修复旧公开仓库；若历史口令曾用于真实服务，请自行轮换。

## 检查方式

```bash
git branch -a
git fsck --full
git log --all --graph --oneline
```

备份路径、源文件校验和、完整 refs 清单与迁移映射在本机交付，不将包含本地敏感配置的备份上传 GitHub。

# 上海服务器 SSH 连接

本流程建立 GitHub Actions 到现有服务器的 SSH 连接。它只验证连接，不更新代码、不重启服务，也不修复 HTTPS 证书。确认现有 DeepTutor 安装方式后，再增加部署步骤。

## 配置

在仓库 Settings → Environments 创建 `shanghai` 环境，建议限制部署分支为 `main`，并在该环境添加 Secrets：

| 名称 | 内容 |
| --- | --- |
| SHANGHAI_SSH_HOST | 服务器公网 IPv4 或域名，不含协议和端口 |
| SHANGHAI_SSH_PORT | SSH 端口；留空时为 22 |
| SHANGHAI_SSH_USER | 服务器登录用户名 |
| SHANGHAI_SSH_PRIVATE_KEY | 专用于本仓库、可非交互使用的 OpenSSH 私钥全文 |
| SHANGHAI_SSH_KNOWN_HOSTS | 已核实的 SSH 主机公钥记录 |

服务器对应用户的 `~/.ssh/authorized_keys` 必须包含部署密钥的公钥。不要覆盖已有公钥。私钥只放在 GitHub Secrets 或受保护的本机密钥文件中，不提交到仓库或聊天。

优先使用单独的部署账号与密钥，并按后续部署操作授予所需权限。不要把个人常用私钥复用于自动化。

## 核实服务器身份

从可信的服务器控制台读取 SSH 主机公钥，例如：

```sh
cat /etc/ssh/ssh_host_ed25519_key.pub
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

`SHANGHAI_SSH_KNOWN_HOSTS` 的记录格式：
- 端口 22：`实际主机名 ssh-ed25519 实际公钥`
- 其他端口：`[实际主机名]:实际端口 ssh-ed25519 实际公钥`

这里的主机名必须与 `SHANGHAI_SSH_HOST` 完全一致。示例中的“实际…”均须替换，不能原样使用。可以使用已验证的其他主机密钥类型。不能把未经独立核验的 `ssh-keyscan` 输出直接当作可信身份。

## 验证

将工作流合并到默认分支后，在 Actions → Shanghai SSH connection check → Run workflow 中选择 main。工作流仅由手动触发，不响应拉取请求或普通推送。

成功日志为：
`SSH authentication and pinned host-key verification passed.`

失败时：
- Missing required setting：补充对应环境 Secret。
- Connection timed out：检查公网地址、端口、路由和安全组；不要为排错直接开放所有端口。
- Permission denied：确认账号、公钥与私钥配对，以及服务器允许密钥认证。
- Host key verification failed：从可信控制台重新核实主机公钥；不要关闭身份验证。

GitHub 托管运行器的出口地址可能变化。若服务器只允许固定来源，可使用受控网络内的自托管运行器或确定的网络出口；不要未经确认修改服务器防火墙。

## 完成标准与下一步

工作流运行成功才表示连接建立。文件已提交、PR 已合并或 Secrets 已保存，都不代表 SSH 实测通过。

后续部署需要确认：DeepTutor 安装目录、部署分支或镜像版本、Docker Compose/systemd 等启动方式、数据目录、备份与健康检查入口。不得猜测目录并运行更新或重启命令。

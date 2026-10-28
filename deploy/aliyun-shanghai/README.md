# 阿里云华东2（上海）部署

目标：现有轻量服务器 Ubuntu-jurf。此前记录为 Ubuntu 24.04、2 vCPU、
2 GiB 内存、40 GiB 磁盘；这些是历史信息，部署前必须实机核查。

本目录是部署准备，不代表服务器已经安装或插件已经连通。

## 部署前实机检查

通过已认证的 Workbench 终端核对主机、地域及运行服务；检查 `free -h`、
`df -h`、`docker ps`、`docker stats --no-stream`、`ss -lntp`。
确认 Docker 可用、3782 未占用，以及官方镜像仓库 ghcr.io 可达。
镜像较大，确认实际下载大小和可用磁盘后再构建。
已有 academic-scholar、浏览器、OAuth、Caddy 等服务必须保留。

Compose 给 DeepTutor 设置 850 MiB 内存上限；这只是隔离上限，不能保证
当前 2 GiB 主机能承载全部服务。若余量不足，先报告实测结果，不停用现有
应用、不自行购买或升级服务器、不自动增加交换空间。

## 启动（仅在实机检查通过后）

在仓库根目录执行：

```sh
sudo python3 deploy/aliyun-shanghai/prepare.py
sudo bash deploy/aliyun-shanghai/run.sh
curl -fsS http://127.0.0.1:3782/api/client-health
```

凭据仅在目标服务器 `/opt/deeptutor/.env` 中生成，不覆盖已有文件，
不输出到终端或聊天。数据保存在 `/opt/deeptutor/data`。
首次网页登录账户为 admin；密码通过服务器的安全凭据管理流程交付。

## HTTPS 与客户端插件

仅绑定本机 `127.0.0.1:3782`。在检查并备份现有 Caddy 配置后，为已验证的
专用域名加入反向代理；不能替换现有 `/mcp`、OAuth 或浏览器路由。
DeepTutor 网页按域名根路径运行，未经适配不能直接挂到现有站点的子路径。
域名、证书及外部可达性尚待现场核验。保持登录验证和 secure cookies 启用。

客户端桥接源码沿用 `deploy/render/client-worker.mjs` 与 `client-tools.json`。
服务地址改为本实例的 HTTPS 域名，密钥只存入私有插件服务端的秘密配置。
Render 目录中的 Dockerfile/bootstrap/接口代码可复用，不依赖 Render 托管。

最后依次验收：容器健康、HTTPS 登录、未授权接口拒绝、私有插件工具发现、
状态查询、真实模型任务完成。模型需在 Settings → Providers 配置并从本机
测试可达性；不从其他现有应用读取或复制 API 密钥。

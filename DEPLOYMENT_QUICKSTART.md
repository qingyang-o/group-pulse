# 生产环境部署快速指南

本文档提供生产环境部署的快速入门指南。完整的安全指南请参考 [DEPLOYMENT_SECURITY_GUIDE.md](DEPLOYMENT_SECURITY_GUIDE.md)。

## 📋 前置要求

- Linux 服务器（Ubuntu 20.04+ / Debian 11+ / CentOS 8+）
- 至少 2GB RAM 和 20GB 磁盘空间
- 域名（可选，用于 HTTPS）
- Root 或 sudo 权限

## 🚀 一键部署

### 1. 下载部署脚本

```bash
# 克隆项目
git clone https://github.com/ZiHuixi/QQgroup-annual-report-analyzer.git
cd QQgroup-annual-report-analyzer

# 或直接下载部署脚本
wget https://raw.githubusercontent.com/ZiHuixi/QQgroup-annual-report-analyzer/main/deploy.sh
chmod +x deploy.sh
```

### 2. 运行部署脚本

```bash
sudo bash deploy.sh
```

脚本将自动完成：
- ✅ 安装系统依赖（Python、Node.js、Nginx、MySQL、Redis）
- ✅ 配置防火墙
- ✅ 创建部署用户
- ✅ 安装应用依赖
- ✅ 构建前端
- ✅ 配置数据库
- ✅ 设置 Systemd 服务
- ✅ 配置 Nginx 反向代理
- ✅ 可选：配置 SSL 证书

### 3. 配置环境变量

部署后需要编辑配置文件：

**必须配置的项目**：

```bash
# Flask 密钥（部署脚本已自动生成）
FLASK_SECRET_KEY=<自动生成的密钥>

# OpenAI API（用于 AI 锐评功能）
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1  # 或国内中转地址

# MySQL 数据库（如果使用 MySQL）
DB_HOST=localhost
DB_PORT=3306
DB_USER=qqreport
DB_PASSWORD=secure_password_here  # 请修改为强密码
DB_NAME=qqreport

# 存储模式
STORAGE_MODE=mysql  # 或 json

# 跨域配置
ALLOWED_ORIGINS=http://yourdomain.com,https://yourdomain.com

# 前端 URL（用于图片生成）
FRONTEND_URL=https://yourdomain.com
```

配置完成后重启服务：

```bash
sudo systemctl restart qqreport
```

## 🔄 应用更新

### 方式一：使用更新脚本（推荐）

```bash
cd /opt/qqgroup-annual-report-analyzer
sudo bash update.sh
```

更新脚本会：
1. 📦 自动备份当前版本
2. 📥 拉取最新代码
3. 📦 更新依赖
4. 🔨 重新构建前端
5. 🗄️ 可选：执行数据库迁移
6. 🔄 重启服务
7. 🏥 健康检查

### 方式二：手动更新

```bash
# 1. 停止服务
sudo systemctl stop qqreport

# 2. 备份
sudo cp -r /opt/qqgroup-annual-report-analyzer /opt/qqreport-backup-$(date +%Y%m%d)

# 3. 拉取最新代码
cd /opt/qqgroup-annual-report-analyzer
sudo -u qqreport git pull

# 4. 更新依赖
sudo -u qqreport venv/bin/pip install -r backend/requirements.txt --upgrade

# 5. 重新构建前端
cd frontend
sudo -u qqreport npm install
sudo -u qqreport npm run build

# 6. 重启服务
sudo systemctl start qqreport
```

### 回滚到上一个版本

如果更新后出现问题：

```bash
sudo bash update.sh --rollback
```

## 📊 服务管理

### 查看服务状态

```bash
sudo systemctl status qqreport
```

### 启动/停止/重启服务

```bash
sudo systemctl start qqreport   # 启动
sudo systemctl stop qqreport    # 停止
sudo systemctl restart qqreport # 重启
sudo systemctl reload qqreport  # 重载配置
```

### 查看日志

```bash
# 实时日志
sudo journalctl -u qqreport -f

# 最近 100 行日志
sudo journalctl -u qqreport -n 100

# 查看错误日志
sudo journalctl -u qqreport -p err
```

### 开机自启

```bash
sudo systemctl enable qqreport  # 启用开机自启
sudo systemctl disable qqreport # 禁用开机自启
```

## 🔒 安全检查清单

部署后请确认以下安全措施：

- [ ] 已修改默认密码（MySQL、Flask Secret Key）
- [ ] 已配置防火墙（只开放 80/443/22 端口）
- [ ] 已配置 SSL 证书（使用 Let's Encrypt）
- [ ] 已设置文件权限（只有 qqreport 用户可写）
- [ ] 已配置速率限制（Flask-Limiter）
- [ ] 已设置日志轮转
- [ ] 已启用自动备份

## 🔐 SSL 证书续期

Let's Encrypt 证书会自动续期，但可以手动测试：

```bash
# 测试续期
sudo certbot renew --dry-run

# 强制续期
sudo certbot renew --force-renewal

# 查看证书状态
sudo certbot certificates
```

**祝部署顺利！** 🎉

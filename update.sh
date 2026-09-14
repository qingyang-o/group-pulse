#!/bin/bash
# QQ群年度报告分析器 - 应用更新脚本

set -e

DEPLOY_DIR="/opt/qqgroup-annual-report-analyzer"
BACKUP_DIR="/opt/qqreport-backups"

echo "========================================"
echo "QQ群年度报告分析器 - 应用更新"
echo "========================================"

# 检查是否在正确的目录
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "❌ 应用目录不存在: $DEPLOY_DIR"
    echo "请先运行部署脚本"
    exit 1
fi

# 备份当前版本
backup_current() {
    echo ""
    echo "📦 备份当前版本..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"
    
    sudo mkdir -p $BACKUP_DIR
    sudo cp -r $DEPLOY_DIR $BACKUP_PATH
    
    # 只保留最近5个备份
    cd $BACKUP_DIR
    sudo ls -t | tail -n +6 | xargs -r sudo rm -rf
    
    echo "✅ 已备份到: $BACKUP_PATH"
}

pull_latest() {
    echo ""
    echo "📥 拉取最新代码..."
    
    cd $DEPLOY_DIR
    sudo -u qqreport git fetch origin
    
    echo ""
    echo "📋 本次更新内容："
    sudo -u qqreport git log HEAD..origin/main --oneline | head -10
    
    echo ""
    read -p "确认更新？(y/n): " confirm
    
    if [ "$confirm" != "y" ]; then
        echo "❌ 取消更新"
        exit 0
    fi
    
    sudo -u qqreport git pull origin main
    echo "✅ 代码已更新"
}

update_dependencies() {
    echo ""
    echo "📦 更新依赖..."
    
    cd $DEPLOY_DIR
    
    echo "🐍 更新 Python 依赖..."
    sudo -u qqreport venv/bin/pip install -r backend/requirements.txt --upgrade
    
    echo "⚛️ 更新前端依赖..."
    cd frontend
    sudo -u qqreport npm install
    
    echo "✅ 依赖已更新"
}

rebuild_frontend() {
    echo ""
    echo "🔨 重新构建前端..."
    
    cd $DEPLOY_DIR/frontend
    sudo -u qqreport npm run build
    
    echo "✅ 前端构建完成"
}

migrate_database() {
    echo ""
    read -p "是否需要执行数据库迁移？(y/n): " need_migrate
    
    if [ "$need_migrate" == "y" ]; then
        echo "🗄️ 执行数据库迁移..."
        cd $DEPLOY_DIR
        sudo -u qqreport venv/bin/python backend/init_db.py
        echo "✅ 数据库迁移完成"
    fi
}

restart_services() {
    echo ""
    echo "🔄 重启服务..."
    
    sudo systemctl restart qqreport
    
    sleep 3
    
    if sudo systemctl is-active --quiet qqreport; then
        echo "✅ 服务重启成功"
    else
        echo "❌ 服务启动失败！"
        echo "查看日志: sudo journalctl -u qqreport -n 50"
        exit 1
    fi
}

health_check() {
    echo ""
    echo "🏥 健康检查..."
    
    sleep 2
    
    if curl -f http://localhost:5000/api/health &>/dev/null; then
        echo "✅ 应用健康检查通过"
    else
        echo "⚠️ 应用可能存在问题，请检查日志"
        echo "查看日志: sudo journalctl -u qqreport -f"
    fi
}

rollback() {
    echo ""
    echo "🔙 回滚到上一个版本..."
    
    LAST_BACKUP=$(ls -t $BACKUP_DIR | head -1)
    
    if [ -z "$LAST_BACKUP" ]; then
        echo "❌ 没有可用的备份"
        exit 1
    fi
    
    echo "回滚到: $LAST_BACKUP"
    read -p "确认回滚？(y/n): " confirm
    
    if [ "$confirm" != "y" ]; then
        echo "❌ 取消回滚"
        exit 0
    fi
    
    sudo systemctl stop qqreport
    sudo rm -rf $DEPLOY_DIR
    sudo cp -r $BACKUP_DIR/$LAST_BACKUP $DEPLOY_DIR
    sudo chown -R qqreport:qqreport $DEPLOY_DIR
    sudo systemctl start qqreport
    
    echo "✅ 已回滚到: $LAST_BACKUP"
}

show_summary() {
    echo ""
    echo "========================================"
    echo "✅ 更新完成！"
    echo "========================================"
    echo ""
    echo "服务状态:"
    sudo systemctl status qqreport --no-pager | grep Active
    echo ""
    echo "日志查看: sudo journalctl -u qqreport -f"
    echo "回滚命令: $0 --rollback"
    echo ""
}

main() {
    case "${1:-}" in
        --rollback)
            rollback
            ;;
        --help)
            echo "用法:"
            echo "  $0           # 执行更新"
            echo "  $0 --rollback  # 回滚到上一个版本"
            echo "  $0 --help      # 显示帮助"
            ;;
        *)
            backup_current
            pull_latest
            update_dependencies
            rebuild_frontend
            migrate_database
            restart_services
            health_check
            show_summary
            ;;
    esac
}

if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

main "$@"

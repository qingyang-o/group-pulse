@echo off
chcp 65001 >nul
echo ========================================
echo QQ群年度报告分析器 - 一键启动
echo ========================================
echo.

:: ========== 1. 检查Python ==========
echo [1/7] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python 3.8+
    echo 下载：https://www.python.org/downloads/
    echo 安装时务必勾选 "Add Python to PATH"
    pause
    exit /b 1
)
echo ✅ Python已安装

:: ========== 2. 检查Node.js ==========
echo.
echo [2/7] 检查Node.js环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Node.js，请先安装Node.js 16+
    echo 下载：https://nodejs.org/
    pause
    exit /b 1
)
echo ✅ Node.js已安装

:: ========== 3. 检查配置文件 ==========
echo.
echo [3/7] 检查配置文件...
if not exist "backend\.env" (
    copy "backend\.env.example" "backend\.env" >nul
    echo ✅ 已创建 backend\.env（默认配置即可用）
) else (
    echo ✅ 配置文件已存在
)

:: ========== 4. Python依赖 ==========
echo.
echo [4/7] 安装Python依赖...
if not exist "venv" (
    echo 创建Python虚拟环境...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo 安装Python依赖包（首次运行需要几分钟）...
pip install -r backend\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo ⚠️  清华源失败，尝试官方源...
    pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo ❌ Python依赖安装失败，请检查网络连接
        echo 可尝试手动运行：pip install -r backend\requirements.txt
        pause
        exit /b 1
    )
)
echo ✅ Python依赖就绪

:: ========== 5. Playwright浏览器 ==========
echo.
echo [5/7] 检查Playwright浏览器...
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(headless=True); p.stop()" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  首次运行，正在下载浏览器（约100MB，请耐心等待）...
    playwright install chromium >nul 2>&1
    if errorlevel 1 (
        echo ⚠️  浏览器下载失败，图片导出可能不可用（不影响报告查看）
    ) else (
        echo ✅ 浏览器安装完成
    )
) else (
    echo ✅ 浏览器已就绪
)

:: ========== 6. 前端依赖 ==========
echo.
echo [6/7] 安装前端依赖...
cd frontend
if not exist "node_modules" (
    echo 安装前端依赖包（首次运行需要几分钟）...
    call npm install --registry=https://registry.npmmirror.com
    if errorlevel 1 (
        echo ⚠️  国内镜像失败，尝试官方源...
        call npm install
        if errorlevel 1 (
            cd ..
            echo ❌ 前端依赖安装失败，请检查网络
            pause
            exit /b 1
        )
    )
)
cd ..
echo ✅ 前端依赖就绪

:: ========== 7. 启动服务 ==========
echo.
echo [7/7] 启动服务...
echo 正在启动后端...
start "QQ群年度报告-后端" cmd /k "cd /d %CD% && venv\Scripts\activate.bat && python backend\app.py"

:: 等待后端就绪
echo 等待后端就绪...
set RETRY=0
:wait_backend
set /a RETRY+=1
if %RETRY% gtr 30 (
    echo ⚠️  后端启动超时，请检查后端窗口报错
    goto start_frontend
)
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:5000/api/health' -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_backend
)
echo ✅ 后端已就绪

:start_frontend
echo 正在启动前端...
start "QQ群年度报告-前端" cmd /k "cd /d %CD%\frontend && npm run dev"
timeout /t 3 /nobreak >nul
echo ✅ 前端已启动

:: 自动打开浏览器
echo.
echo 正在打开浏览器...
start http://localhost:5173

echo.
echo ========================================
echo 🎉 启动完成！
echo ========================================
echo 📱 报告页面：http://localhost:5173
echo 🔧 后端API：http://localhost:5000
echo.
echo 📋 使用流程：
echo    1. 用 qq-chat-exporter 导出群聊记录为JSON
echo       下载：https://github.com/shuakami/qq-chat-exporter
echo    2. 在网页上传JSON文件
echo    3. 选择热词，生成年度报告
echo    4. 点击"生成图片分享"导出长图
echo.
echo 💡 关闭两个黑色窗口即可停止服务
echo ========================================
echo.
pause

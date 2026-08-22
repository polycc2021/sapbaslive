import os
import sys
import time
import json

from playwright.sync_api import sync_playwright


# ============================================================
# 环境变量
# ============================================================

BAS_URL = os.getenv(
    "BAS_URL",
    "https://9a18409etrial.us10cf.trial.applicationstudio.cloud.sap"
).rstrip("/")

BAS_USERNAME = os.getenv("BAS_USERNAME")
BAS_PASSWORD = os.getenv("BAS_PASSWORD")

DEVSPACE_NAME = os.getenv(
    "BAS_DEVSPACE",
    "chixu"
)

DEVSPACE_ID = os.getenv(
    "BAS_DEVSPACE_ID",
    "ws-20y5a"
)


# ============================================================
# 日志
# ============================================================

def log(message):
    print(f"[BAS] {message}", flush=True)


# ============================================================
# 检查环境变量
# ============================================================

def check_environment():

    missing = []

    if not BAS_URL:
        missing.append("BAS_URL")

    if not BAS_USERNAME:
        missing.append("BAS_USERNAME")

    if not BAS_PASSWORD:
        missing.append("BAS_PASSWORD")

    if not DEVSPACE_ID:
        missing.append("BAS_DEVSPACE_ID")

    if missing:

        log(
            "缺少 GitHub Secrets："
            + ", ".join(missing)
        )

        sys.exit(1)


# ============================================================
# 找用户名输入框
# ============================================================

def find_username_input(page):

    selectors = [
        'input[type="email"]',
        'input[name="email"]',
        'input[name="username"]',
        'input[autocomplete="username"]',
        'input[placeholder*="Email"]',
        'input[placeholder*="email"]',
        'input[placeholder*="User"]',
        'input[placeholder*="user"]'
    ]

    for selector in selectors:

        try:

            locator = page.locator(
                selector
            ).first

            if locator.is_visible(
                timeout=1000
            ):

                return locator

        except Exception:
            pass

    return None


# ============================================================
# 找密码输入框
# ============================================================

def find_password_input(page):

    selectors = [
        'input[type="password"]',
        'input[name="password"]',
        'input[autocomplete="current-password"]'
    ]

    for selector in selectors:

        try:

            locator = page.locator(
                selector
            ).first

            if locator.is_visible(
                timeout=1000
            ):

                return locator

        except Exception:
            pass

    return None


# ============================================================
# 点击 Continue / Sign In
# ============================================================

def click_continue(page):

    selectors = [
        'button:has-text("Continue")',
        'button:has-text("Sign In")',
        'button:has-text("Sign in")',
        'button:has-text("Log On")',
        'button[type="submit"]',
        'input[type="submit"]'
    ]

    for selector in selectors:

        try:

            button = page.locator(
                selector
            ).first

            if button.is_visible(
                timeout=1000
            ):

                button.click()

                return True

        except Exception:
            pass

    try:

        page.keyboard.press("Enter")

        return True

    except Exception:

        return False


# ============================================================
# SAP 登录
# ============================================================

def login(page):

    log(
        "打开 SAP Business Application Studio..."
    )

    page.goto(
        BAS_URL + "/index.html",
        wait_until="domcontentloaded",
        timeout=120000
    )

    log(
        f"初始页面：{page.url}"
    )

    page.wait_for_timeout(5000)

    log(
        f"当前页面：{page.url}"
    )

    # --------------------------------------------------------
    # 用户名
    # --------------------------------------------------------

    username_input = find_username_input(
        page
    )

    if username_input:

        log(
            "发现 SAP 用户名输入框。"
        )

        username_input.fill(
            BAS_USERNAME
        )

        log(
            "用户名已经填写。"
        )

        click_continue(
            page
        )

        page.wait_for_timeout(
            3000
        )

    # --------------------------------------------------------
    # 密码
    # --------------------------------------------------------

    password_input = find_password_input(
        page
    )

    if password_input:

        log(
            "发现 SAP 密码输入框。"
        )

        password_input.fill(
            BAS_PASSWORD
        )

        log(
            "密码已经填写。"
        )

        click_continue(
            page
        )

    # --------------------------------------------------------
    # 等待登录完成
    # --------------------------------------------------------

    log(
        "等待 SAP 完成登录..."
    )

    for i in range(30):

        page.wait_for_timeout(
            2000
        )

        current_url = page.url

        log(
            f"登录等待 {i + 1}/30：{current_url}"
        )

        if (
            "applicationstudio.cloud.sap"
            in current_url
            and
            "accounts.sap.com"
            not in current_url
        ):

            log(
                "SAP 登录成功。"
            )

            return True

    log(
        "SAP 登录失败。"
    )

    try:

        page.screenshot(
            path="sap_login_failed.png",
            full_page=True
        )

    except Exception:
        pass

    return False


# ============================================================
# 获取 JWT
# ============================================================

def get_jwt(context):

    log(
        "获取 SAP BAS JWT..."
    )

    response = context.request.get(
        BAS_URL + "/jwt",
        timeout=60000
    )

    log(
        f"JWT HTTP 状态码：{response.status}"
    )

    if response.status != 200:

        log(
            response.text()[:3000]
        )

        return None

    try:

        data = response.json()

    except Exception:

        text = response.text().strip()

        if text:
            return text

        return None

    if isinstance(data, dict):

        if data.get("value"):
            return data["value"]

        if data.get("token"):
            return data["token"]

        if data.get("jwt"):
            return data["jwt"]

    if isinstance(data, str):

        return data

    return None


# ============================================================
# 查询 Workspace
# ============================================================

def get_workspace(context, jwt):

    url = (
        BAS_URL
        + "/ws-manager/api/v1/workspace?all=true"
    )

    log(
        "查询 Dev Space..."
    )

    response = context.request.get(
        url,
        headers={
            "X-Approuter-Authorization":
                f"Bearer {jwt}"
        },
        timeout=60000
    )

    log(
        f"Workspace API 状态码：{response.status}"
    )

    if response.status != 200:

        log(
            response.text()[:5000]
        )

        return None

    try:

        data = response.json()

    except Exception as e:

        log(
            f"JSON 解析失败：{e}"
        )

        return None

    if not isinstance(data, list):

        log(
            "Workspace API 返回格式异常。"
        )

        return None

    log(
        f"API 返回 Workspace 数量：{len(data)}"
    )

    # ========================================================
    # 查找目标 Dev Space
    # ========================================================

    for workspace in data:

        if not isinstance(
            workspace,
            dict
        ):
            continue

        config = workspace.get(
            "config",
            {}
        )

        labels = config.get(
            "labels",
            {}
        )

        workspace_id = config.get(
            "id"
        )

        username = config.get(
            "username"
        )

        display_name = labels.get(
            "ws-manager.devx.sap.com/displayname"
        )

        log(
            "------------------------------------------"
        )

        log(
            f"Workspace ID : {workspace_id}"
        )

        log(
            f"Display Name : {display_name}"
        )

        log(
            f"Username     : {username}"
        )

        # ----------------------------------------------------
        # ID 匹配
        # ----------------------------------------------------

        if (
            str(workspace_id)
            == str(DEVSPACE_ID)
        ):

            log(
                "找到目标 Dev Space！"
            )

            return workspace

        # ----------------------------------------------------
        # 名称匹配
        # ----------------------------------------------------

        if (
            display_name
            and
            str(display_name)
            == str(DEVSPACE_NAME)
        ):

            log(
                "通过名称找到目标 Dev Space！"
            )

            return workspace

    log(
        "没有找到目标 Dev Space。"
    )

    return None


# ============================================================
# 获取 Dev Space 状态
# ============================================================

def get_status(workspace):

    if not workspace:
        return "UNKNOWN"

    runtime = workspace.get(
        "runtime",
        {}
    )

    status = runtime.get(
        "status"
    )

    if status:

        status = str(
            status
        ).upper()

        log(
            f"Runtime 状态：{status}"
        )

        return status

    # 如果 runtime.status 没有，再看 suspended
    config = workspace.get(
        "config",
        {}
    )

    suspended = config.get(
        "suspended"
    )

    if suspended is True:
        return "STOPPED"

    if suspended is False:
        return "RUNNING"

    return "UNKNOWN"


# ============================================================
# 启动 Dev Space
# ============================================================

def start_workspace(
    context,
    jwt,
    workspace
):

    config = workspace.get(
        "config",
        {}
    )

    labels = config.get(
        "labels",
        {}
    )

    workspace_id = config.get(
        "id"
    )

    username = config.get(
        "username"
    )

    display_name = labels.get(
        "ws-manager.devx.sap.com/displayname"
    )

    if not workspace_id:

        log(
            "无法启动：缺少 Workspace ID。"
        )

        return False

    if not username:

        log(
            "无法启动：缺少 Workspace username。"
        )

        return False

    if not display_name:

        # 如果 API 没有返回名称，则使用 Secret
        display_name = DEVSPACE_NAME

    # ========================================================
    # SAP 官方 API
    # ========================================================

    url = (
        BAS_URL
        + "/ws-manager/api/v1/workspace/"
        + workspace_id
        + "?all=false&username="
        + username
    )

    log(
        "=========================================="
    )

    log(
        "启动 Dev Space..."
    )

    log(
        f"Workspace ID : {workspace_id}"
    )

    log(
        f"Username     : {username}"
    )

    log(
        f"Display Name : {display_name}"
    )

    log(
        f"启动 URL     : {url}"
    )

    payload = {
        "suspended": False,
        "WorkspaceDisplayName": display_name
    }

    response = context.request.put(
        url,
        headers={
            "X-Approuter-Authorization":
                f"Bearer {jwt}",
            "Content-Type":
                "application/json"
        },
        data=json.dumps(
            payload
        ),
        timeout=60000
    )

    log(
        f"启动 API 状态码：{response.status}"
    )

    if response.status not in [
        200,
        201,
        202
    ]:

        log(
            "Dev Space 启动失败："
        )

        log(
            response.text()[:5000]
        )

        return False

    log(
        "Dev Space 启动请求成功！"
    )

    return True


# ============================================================
# 等待 Dev Space RUNNING
# ============================================================

def wait_until_running(
    context,
    jwt,
    timeout_seconds=360
):

    log(
        "等待 Dev Space 启动..."
    )

    start_time = time.time()

    while (
        time.time() - start_time
        < timeout_seconds
    ):

        workspace = get_workspace(
            context,
            jwt
        )

        if not workspace:

            time.sleep(10)

            continue

        status = get_status(
            workspace
        )

        log(
            f"当前 Dev Space 状态：{status}"
        )

        if status in [
            "RUNNING",
            "STARTED"
        ]:

            log(
                "Dev Space 已经 RUNNING！"
            )

            return workspace

        if status in [
            "ERROR",
            "FAILED"
        ]:

            log(
                "Dev Space 启动进入错误状态。"
            )

            return None

        time.sleep(10)

    log(
        "等待 Dev Space RUNNING 超时。"
    )

    return None


# ============================================================
# 打开 Workspace 并触发 Web Shell / 启动脚本
# ============================================================

def open_workspace(
    page,
    context,
    jwt,
    workspace
):

    runtime = workspace.get(
        "runtime",
        {}
    )

    workspace_url = (
        runtime
        .get("url", {})
        .get("theia")
    )

    # 如果 API 没有提供 URL，使用空间专属路由
    if not workspace_url:

        workspace_url = (
            BAS_URL
            + "/"
            + DEVSPACE_ID
        )

    log(
        "打开 Dev Space Workspace 并激活 Web Shell..."
    )

    log(
        f"Workspace URL：{workspace_url}"
    )

    # --------------------------------------------------------
    # 1. API 穿透触发：直接请求 Dev Space 实例路由
    # --------------------------------------------------------
    try:

        log("发送 AppRouter 会话激活 API 请求...")

        headers = {
            "X-Approuter-Authorization": f"Bearer {jwt}",
            "Authorization": f"Bearer {jwt}"
        }

        context.request.get(
            f"{BAS_URL}/{DEVSPACE_ID}",
            headers=headers,
            timeout=30000
        )

        context.request.get(
            f"{BAS_URL}/ws-manager/api/v1/workspace/{DEVSPACE_ID}/instance",
            headers=headers,
            timeout=30000
        )

        log("API 触发请求已成功发出。")

    except Exception as e:

        log(f"API 触发提示（不影响后续页面加载）：{e}")

    # --------------------------------------------------------
    # 2. 浏览器打开 Web IDE 并留出 Shell 挂载初始化时间
    # --------------------------------------------------------
    try:

        page.goto(
            workspace_url,
            wait_until="domcontentloaded",
            timeout=120000
        )

        # 保持页面打开 20 秒，让 AppRouter 与后台 Terminal / Web Shell 完全完成初始化
        # 此时会触发容器读取 ~/.bashrc 并运行 ~/my-node/start.sh
        page.wait_for_timeout(
            20000
        )

        log(
            f"Workspace 当前页面：{page.url}"
        )

        log(
            "Workspace 访问完成，Web Shell 已激活联动！"
        )

        return True

    except Exception as e:

        log(
            f"打开 Workspace 失败：{e}"
        )

        return False


# ============================================================
# 主程序
# ============================================================

def main():

    log(
        "=========================================="
    )

    log(
        " SAP BAS Dev Space Keep Alive"
    )

    log(
        "=========================================="
    )

    check_environment()

    log(
        f"BAS URL      : {BAS_URL}"
    )

    log(
        f"Dev Space    : {DEVSPACE_NAME}"
    )

    log(
        f"Dev Space ID : {DEVSPACE_ID}"
    )

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            viewport={
                "width": 1366,
                "height": 768
            }
        )

        page = context.new_page()

        try:

            # =================================================
            # 1. 登录
            # =================================================

            if not login(page):

                log(
                    "登录失败，任务结束。"
                )

                sys.exit(1)

            # =================================================
            # 2. JWT
            # =================================================

            jwt = get_jwt(
                context
            )

            if not jwt:

                log(
                    "获取 JWT 失败。"
                )

                sys.exit(1)

            log(
                "JWT 获取成功。"
            )

            # =================================================
            # 3. 查询 Workspace
            # =================================================

            workspace = get_workspace(
                context,
                jwt
            )

            if not workspace:

                sys.exit(1)

            # =================================================
            # 4. 判断状态
            # =================================================

            status = get_status(
                workspace
            )

            log(
                f"{DEVSPACE_NAME} 当前状态：{status}"
            )

            # =================================================
            # 5. STOPPED → 启动
            # =================================================

            if status == "STOPPED":

                log(
                    "检测到 Dev Space 已停止。"
                )

                success = start_workspace(
                    context,
                    jwt,
                    workspace
                )

                if not success:

                    sys.exit(1)

                workspace = wait_until_running(
                    context,
                    jwt
                )

                if not workspace:

                    sys.exit(1)

            # =================================================
            # 6. STARTING
            # =================================================

            elif status in [
                "STARTING",
                "CREATING"
            ]:

                log(
                    "Dev Space 正在启动。"
                )

                workspace = wait_until_running(
                    context,
                    jwt
                )

                if not workspace:

                    sys.exit(1)

            # =================================================
            # 7. RUNNING
            # =================================================

            elif status in [
                "RUNNING",
                "STARTED"
            ]:

                log(
                    "Dev Space 已经处于 RUNNING。"
                )

            else:

                log(
                    f"未知 Dev Space 状态：{status}"
                )

            # =================================================
            # 8. 最终检查
            # =================================================

            workspace = get_workspace(
                context,
                jwt
            )

            if not workspace:

                sys.exit(1)

            final_status = get_status(
                workspace
            )

            log(
                f"最终状态：{final_status}"
            )

            if final_status not in [
                "RUNNING",
                "STARTED"
            ]:

                log(
                    "Dev Space 最终没有进入 RUNNING。"
                )

                sys.exit(1)

            # =================================================
            # 9. 打开 Workspace 并触发 Shell
            # =================================================

            def open_workspace(
    page,
    context,
    jwt,
    workspace
):

    runtime = workspace.get(
        "runtime",
        {}
    )

    workspace_url = (
        runtime
        .get("url", {})
        .get("theia")
    )

    if not workspace_url:

        workspace_url = (
            BAS_URL
            + "/"
            + DEVSPACE_ID
        )

    log("==========================================")
    log("打开 Dev Space Workspace")
    log(f"Workspace URL：{workspace_url}")
    log("==========================================")

    # --------------------------------------------------------
    # 1. 打开 Workspace
    # --------------------------------------------------------

    try:

        page.goto(
            workspace_url,
            wait_until="domcontentloaded",
            timeout=120000
        )

        log(
            f"Workspace 页面已打开：{page.url}"
        )

    except Exception as e:

        log(
            f"Workspace 页面打开失败：{e}"
        )

        return False

    # --------------------------------------------------------
    # 2. 等待 VS Code / OpenVSCode Server 初始化
    # --------------------------------------------------------

    log(
        "等待 VS Code Workspace 初始化..."
    )

    page.wait_for_timeout(
        15000
    )

    # --------------------------------------------------------
    # 3. 检查页面标题
    # --------------------------------------------------------

    try:

        log(
            f"Workspace 页面标题：{page.title()}"
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # 4. 尝试打开 Terminal
    # --------------------------------------------------------

    terminal_opened = False

    terminal_selectors = [

        # VS Code / OpenVSCode Server
        'text=Terminal',

        # 菜单
        '[aria-label*="Terminal"]',

        # Terminal 菜单项
        '[role="menuitem"]:has-text("Terminal")',

        # 新终端
        'text=New Terminal',

        # 命令面板
        '[aria-label*="Command"]'
    ]

    for selector in terminal_selectors:

        try:

            locator = page.locator(
                selector
            ).first

            if locator.is_visible(
                timeout=2000
            ):

                log(
                    f"发现 Terminal UI：{selector}"
                )

                locator.click()

                terminal_opened = True

                break

        except Exception:
            pass

    # --------------------------------------------------------
    # 5. 如果没有直接找到 Terminal，使用快捷键
    # --------------------------------------------------------

    if not terminal_opened:

        try:

            log(
                "没有找到 Terminal 按钮，尝试快捷键..."
            )

            # VS Code 新建 Terminal：
            # Ctrl + Shift + `
            page.keyboard.press(
                "Control+Shift+`"
            )

            terminal_opened = True

        except Exception as e:

            log(
                f"快捷键打开 Terminal 失败：{e}"
            )

    # --------------------------------------------------------
    # 6. 给 Bash / .bashrc 留出时间
    # --------------------------------------------------------

    if terminal_opened:

        log(
            "Terminal 已触发，等待 Bash 初始化..."
        )

        page.wait_for_timeout(
            10000
        )

    else:

        log(
            "警告：没有成功触发 Terminal。"
        )

    # --------------------------------------------------------
    # 7. 最终页面状态
    # --------------------------------------------------------

    log(
        f"Workspace 当前页面：{page.url}"
    )

    log(
        "Workspace 初始化流程完成。"
    )

    return terminal_opened

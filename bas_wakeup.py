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
# 在 Dev Space Manager 页面点击空间名字（最接近手动操作）
# ============================================================

def click_devspace_in_manager(page):
    """
    回到 index.html / Dev Space Manager，模拟手动点击空间名字。
    这是激活节点最可靠的方式之一。
    """

    log("回到 Dev Space Manager 页面，准备点击空间名字...")

    try:
        page.goto(
            BAS_URL + "/index.html",
            wait_until="domcontentloaded",
            timeout=120000
        )
        page.wait_for_timeout(8000)
    except Exception as e:
        log(f"打开 Manager 页面失败：{e}")
        return False

    # 多种可能的选择器（BAS UI 会变，尽量覆盖）
    name_selectors = [
        f'text="{DEVSPACE_NAME}"',
        f'a:has-text("{DEVSPACE_NAME}")',
        f'span:has-text("{DEVSPACE_NAME}")',
        f'div:has-text("{DEVSPACE_NAME}")',
        f'[title="{DEVSPACE_NAME}"]',
        f'*:has-text("{DEVSPACE_NAME}")',
    ]

    for selector in name_selectors:
        try:
            loc = page.locator(selector).first
            if loc.is_visible(timeout=3000):
                log(f"找到空间名字元素，使用选择器：{selector}")
                loc.click(timeout=5000)
                log("已点击空间名字，等待 IDE 加载...")
                page.wait_for_timeout(15000)
                return True
        except Exception:
            continue

    # 如果 iframe 里（老版 UI 常见）
    try:
        frames = page.frames
        for frame in frames:
            for selector in name_selectors:
                try:
                    loc = frame.locator(selector).first
                    if loc.is_visible(timeout=2000):
                        log(f"在 iframe 中找到空间名字：{selector}")
                        loc.click(timeout=5000)
                        log("已点击空间名字（iframe），等待 IDE 加载...")
                        page.wait_for_timeout(15000)
                        return True
                except Exception:
                    continue
    except Exception as e:
        log(f"iframe 查找提示：{e}")

    log("未能在 Manager 页面点击到空间名字，将改用直接打开 workspace URL。")
    return False


# ============================================================
# 打开 Terminal，真正触发 shell / bashrc / start.sh
# ============================================================

def open_terminal_and_activate(page):
    """
    在已打开的 Theia / BAS IDE 中打开集成终端。
    打开终端会完整挂载用户 shell，从而执行 ~/.bashrc 和 start.sh。
    """

    log("尝试在 IDE 中打开 Terminal 以激活节点...")

    # 等待 IDE 主界面出现（常见 Theia / VS Code 类选择器）
    ide_ready_selectors = [
        ".theia-app-shell",
        "#theia-app-shell",
        ".monaco-workbench",
        ".theia-MainToolbar",
        "[class*='theia']",
        "body",
    ]

    ready = False
    for sel in ide_ready_selectors:
        try:
            page.wait_for_selector(sel, timeout=20000)
            ready = True
            log(f"IDE 已就绪（检测到 {sel}）")
            break
        except Exception:
            continue

    if not ready:
        log("未检测到典型 IDE 元素，但仍尝试打开 Terminal。")

    page.wait_for_timeout(5000)

    # 方法 1：键盘快捷键 Ctrl+` （最通用）
    try:
        log("使用快捷键 Ctrl+` 打开 Terminal...")
        page.keyboard.press("Control+`")
        page.wait_for_timeout(5000)
        log("快捷键已发送。")
    except Exception as e:
        log(f"快捷键失败：{e}")

    # 方法 2：Command Palette → Terminal: Create New Terminal
    try:
        log("尝试 Command Palette 打开 Terminal...")
        page.keyboard.press("Control+Shift+P")
        page.wait_for_timeout(2000)

        # 输入命令
        page.keyboard.type("Terminal: Create New Terminal", delay=50)
        page.wait_for_timeout(1500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(5000)
        log("Command Palette 命令已执行。")
    except Exception as e:
        log(f"Command Palette 方式提示：{e}")

    # 方法 3：菜单点击（如果可见）
    menu_selectors = [
        'text=Terminal',
        'li:has-text("Terminal")',
        '[aria-label*="Terminal"]',
        'a:has-text("Terminal")',
    ]
    for sel in menu_selectors:
        try:
            menu = page.locator(sel).first
            if menu.is_visible(timeout=2000):
                menu.click()
                page.wait_for_timeout(1000)
                # 再点 New Terminal
                new_term = page.locator('text=New Terminal').first
                if new_term.is_visible(timeout=2000):
                    new_term.click()
                    log("通过菜单打开了 New Terminal。")
                    page.wait_for_timeout(5000)
                    break
        except Exception:
            continue

    # 给 shell 足够时间执行 ~/.bashrc 和 start.sh
    log("等待 shell 初始化并执行 start.sh（约 25 秒）...")
    page.wait_for_timeout(25000)

    log("Terminal 激活流程完成。")
    return True


# ============================================================
# 打开 Workspace 并触发 Web Shell / 启动脚本（增强版）
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
        "=========================================="
    )
    log(
        "打开 Dev Space Workspace 并激活节点..."
    )
    log(
        f"Workspace URL：{workspace_url}"
    )

    # --------------------------------------------------------
    # 1. API 穿透触发（辅助）
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

        # 再请求一次 theia 相关路径
        if workspace_url:
            context.request.get(
                workspace_url,
                headers=headers,
                timeout=30000
            )

        log("API 触发请求已成功发出。")

    except Exception as e:

        log(f"API 触发提示（不影响后续页面加载）：{e}")

    # --------------------------------------------------------
    # 2. 优先模拟「手动点击空间名字」
    # --------------------------------------------------------
    clicked = click_devspace_in_manager(page)

    # --------------------------------------------------------
    # 3. 如果点击失败，直接 goto workspace_url
    # --------------------------------------------------------
    if not clicked:
        log("改用直接打开 Workspace URL...")
        try:
            page.goto(
                workspace_url,
                wait_until="domcontentloaded",
                timeout=120000
            )
            page.wait_for_timeout(15000)
        except Exception as e:
            log(f"直接打开 Workspace 失败：{e}")
            return False

    # 确认当前是否已经进入 IDE
    current = page.url
    log(f"当前页面 URL：{current}")

    # 如果还在 manager，再强制跳一次
    if "index.html" in current or "ws-manager" in current or DEVSPACE_NAME in current and "theia" not in current.lower():
        log("仍可能在 Manager 页面，强制跳转到 workspace_url...")
        try:
            page.goto(
                workspace_url,
                wait_until="domcontentloaded",
                timeout=120000
            )
            page.wait_for_timeout(12000)
        except Exception as e:
            log(f"强制跳转提示：{e}")

    # --------------------------------------------------------
    # 4. 打开 Terminal，真正激活 shell 与 start.sh
    # --------------------------------------------------------
    open_terminal_and_activate(page)

    # --------------------------------------------------------
    # 5. 额外保持一段时间，确保后台进程稳定
    # --------------------------------------------------------
    log("额外保持页面打开 20 秒，确保节点完全激活...")
    page.wait_for_timeout(20000)

    log(
        f"Workspace 最终页面：{page.url}"
    )

    log(
        "Workspace 访问完成，节点激活流程已执行！"
    )

    return True


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
            # 9. 打开 Workspace 并触发 Shell（增强版）
            # =================================================

            open_workspace(
                page,
                context,
                jwt,
                workspace
            )

            log(
                "=========================================="
            )

            log(
                " Keep Alive 执行成功"
            )

            log(
                f" Dev Space : {DEVSPACE_NAME}"
            )

            log(
                " 状态      : RUNNING"
            )

            log(
                " Workspace : 已访问且已触发节点联动"
            )

            log(
                "=========================================="
            )

        except Exception as e:

            log(
                "程序发生异常："
            )

            log(
                str(e)
            )

            try:

                page.screenshot(
                    path="bas_error.png",
                    full_page=True
                )

            except Exception:
                pass

            sys.exit(1)

        finally:

            context.close()
            browser.close()


if __name__ == "__main__":
    main()

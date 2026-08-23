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

        if (
            str(workspace_id)
            == str(DEVSPACE_ID)
        ):

            log(
                "找到目标 Dev Space！"
            )

            return workspace

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

        display_name = DEVSPACE_NAME

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
# 在 Dev Space Manager 页面强力点击空间名字
# ============================================================

def click_devspace_in_manager(page):
    """
    回到 index.html，用多种方式找到并点击空间名字/卡片。
    这是建立正确会话最可靠的方式。
    """

    log("回到 Dev Space Manager 页面，准备点击空间名字...")

    try:
        page.goto(
            BAS_URL + "/index.html",
            wait_until="domcontentloaded",
            timeout=120000
        )
        page.wait_for_timeout(12000)
    except Exception as e:
        log(f"打开 Manager 页面失败：{e}")
        return False

    # 打印当前页面信息，方便调试
    try:
        log(f"Manager 页面标题：{page.title()}")
        log(f"Manager 页面 URL：{page.url}")
        body_preview = page.locator("body").inner_text(timeout=3000)[:300]
        log(f"Manager 页面内容预览：{body_preview!r}")
    except Exception as e:
        log(f"获取 Manager 页面信息失败：{e}")

    # 截图 Manager 页面
    try:
        page.screenshot(path="bas_manager.png", full_page=True)
        log("已保存 Manager 截图：bas_manager.png")
    except Exception:
        pass

    # 更全面的选择器
    candidates = [
        # 精确名字
        page.get_by_text(DEVSPACE_NAME, exact=True),
        page.locator(f'text="{DEVSPACE_NAME}"'),
        page.locator(f'a:has-text("{DEVSPACE_NAME}")'),
        page.locator(f'span:has-text("{DEVSPACE_NAME}")'),
        page.locator(f'div:has-text("{DEVSPACE_NAME}")'),
        page.locator(f'[title="{DEVSPACE_NAME}"]'),
        page.locator(f'[aria-label*="{DEVSPACE_NAME}"]'),
        # 带 ID
        page.locator(f'text="{DEVSPACE_ID}"'),
        page.locator(f'*:has-text("{DEVSPACE_ID}")'),
        # 模糊
        page.get_by_text(DEVSPACE_NAME, exact=False),
    ]

    for i, loc in enumerate(candidates):
        try:
            if loc.count() > 0:
                first = loc.first
                if first.is_visible(timeout=2000):
                    log(f"找到可点击元素（候选 {i}），准备点击...")
                    first.scroll_into_view_if_needed()
                    page.wait_for_timeout(1000)
                    first.click(timeout=8000, force=True)
                    log("已点击空间名字/卡片，等待跳转...")
                    page.wait_for_timeout(25000)
                    return True
        except Exception as e:
            log(f"候选 {i} 点击失败：{e}")
            continue

    # iframe 兜底
    try:
        for frame in page.frames:
            try:
                loc = frame.get_by_text(DEVSPACE_NAME, exact=False)
                if loc.count() > 0 and loc.first.is_visible(timeout=2000):
                    log("在 iframe 中找到空间名字，点击...")
                    loc.first.click(timeout=5000, force=True)
                    page.wait_for_timeout(25000)
                    return True
            except Exception:
                continue
    except Exception as e:
        log(f"iframe 查找提示：{e}")

    log("未能在 Manager 页面点击到空间名字。")
    return False


# ============================================================
# 等待 IDE 真正加载完成
# ============================================================

def wait_for_ide_ready(page, max_wait_seconds=120):

    log(f"开始等待 IDE 真正就绪（最长 {max_wait_seconds} 秒）...")

    ide_selectors = [
        ".theia-app-shell",
        "#theia-app-shell",
        ".monaco-workbench",
        ".theia-MainToolbar",
        ".p-Widget.theia-app-shell",
        ".monaco-editor",
        ".codicon",
        "div[class*='theia']",
        "div[class*='monaco']",
        "div[class*='workbench']",
        ".lm-Widget",
    ]

    start = time.time()
    attempt = 0

    while time.time() - start < max_wait_seconds:
        attempt += 1
        elapsed = int(time.time() - start)

        for sel in ide_selectors:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0 and loc.is_visible(timeout=400):
                    log(f"IDE 已就绪！检测到元素：{sel}（耗时 {elapsed}s）")
                    return True
            except Exception:
                pass

        try:
            title = page.title()
            url = page.url
            if title and any(k in title.lower() for k in ["business application studio", "theia", "code editor", "bas"]):
                log(f"通过标题判断 IDE 可能已加载：{title}（耗时 {elapsed}s）")
                page.wait_for_timeout(8000)
                return True
            if "theia-workspaces" in url.lower() and "index.html" not in url:
                pass
        except Exception:
            pass

        try:
            body_text = page.locator("body").inner_text(timeout=1500)
            if body_text and len(body_text.strip()) > 80:
                log(f"页面已有内容（{len(body_text)} 字符），认为已加载（耗时 {elapsed}s）")
                page.wait_for_timeout(5000)
                return True
        except Exception:
            pass

        if attempt % 4 == 0:
            log(f"仍在等待 IDE... 已等待 {elapsed}s，URL：{page.url}")

        page.wait_for_timeout(3000)

    log(f"等待 IDE 超时（{max_wait_seconds}s）")
    return False


# ============================================================
# 打开 Terminal
# ============================================================

def open_terminal_and_activate(page):

    log("尝试在 IDE 中打开 Terminal 以激活节点...")

    wait_for_ide_ready(page, max_wait_seconds=90)

    page.wait_for_timeout(4000)

    # 快捷键
    try:
        log("使用快捷键 Ctrl+` 打开 Terminal...")
        page.keyboard.press("Control+`")
        page.wait_for_timeout(3000)
        page.keyboard.press("Control+Shift+`")
        page.wait_for_timeout(3000)
    except Exception as e:
        log(f"快捷键失败：{e}")

    # Command Palette
    try:
        log("尝试 Command Palette 打开 Terminal...")
        page.keyboard.press("Control+Shift+P")
        page.wait_for_timeout(2000)
        page.keyboard.press("Control+A")
        page.keyboard.type("Terminal: Create New Terminal", delay=25)
        page.wait_for_timeout(1200)
        page.keyboard.press("Enter")
        page.wait_for_timeout(4000)
    except Exception as e:
        log(f"Command Palette 提示：{e}")

    # 再试一次
    try:
        page.keyboard.press("Control+`")
        page.wait_for_timeout(2000)
    except Exception:
        pass

    log("等待 shell 初始化并执行 start.sh（约 40 秒）...")
    page.wait_for_timeout(40000)

    log("Terminal 激活流程完成。")
    return True


# ============================================================
# 打开 Workspace（核心增强版）
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

    if not workspace_url:
        workspace_url = (
            BAS_URL
            + "/"
            + DEVSPACE_ID
        )

    log("==========================================")
    log("打开 Dev Space Workspace 并激活节点...")
    log(f"Workspace URL：{workspace_url}")

    # 1. API 辅助触发
    try:
        log("发送 AppRouter 会话激活 API 请求...")
        headers = {
            "X-Approuter-Authorization": f"Bearer {jwt}",
            "Authorization": f"Bearer {jwt}"
        }
        context.request.get(f"{BAS_URL}/{DEVSPACE_ID}", headers=headers, timeout=30000)
        context.request.get(
            f"{BAS_URL}/ws-manager/api/v1/workspace/{DEVSPACE_ID}/instance",
            headers=headers,
            timeout=30000
        )
        if workspace_url:
            context.request.get(workspace_url, headers=headers, timeout=30000)
        log("API 触发请求已成功发出。")
    except Exception as e:
        log(f"API 触发提示：{e}")

    # 2. 优先走「点击空间名字」链路（建立正确会话）
    clicked = click_devspace_in_manager(page)

    # 3. 如果点击失败，带 JWT 头直接打开
    if not clicked:
        log("改用直接打开 Workspace URL（带 Authorization 头）...")
        try:
            page.set_extra_http_headers({
                "Authorization": f"Bearer {jwt}",
                "X-Approuter-Authorization": f"Bearer {jwt}"
            })
            page.goto(
                workspace_url,
                wait_until="domcontentloaded",
                timeout=180000
            )
        except Exception as e:
            log(f"直接打开失败：{e}")

    # 4. 长时间等待 + 检测白屏
    log("页面已跳转，开始长时间等待 IDE 加载...")
    page.wait_for_timeout(20000)

    try:
        page.wait_for_load_state("networkidle", timeout=60000)
        log("networkidle 已到达。")
    except Exception:
        log("networkidle 超时，继续。")

    page.wait_for_timeout(15000)

    # 打印当前状态
    try:
        log(f"当前 URL：{page.url}")
        log(f"当前标题：{page.title()}")
        body_text = page.locator("body").inner_text(timeout=3000)
        log(f"页面文本长度：{len(body_text)}，预览：{body_text[:200]!r}")
    except Exception as e:
        log(f"获取页面信息失败：{e}")
        body_text = ""

    # 5. 如果是白屏，尝试 reload 一次
    if not body_text or len(body_text.strip()) < 30:
        log("检测到疑似白屏，尝试 reload...")
        try:
            page.reload(wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(25000)
            try:
                page.wait_for_load_state("networkidle", timeout=45000)
            except Exception:
                pass
            page.wait_for_timeout(15000)

            body_text = page.locator("body").inner_text(timeout=3000)
            log(f"reload 后文本长度：{len(body_text)}，预览：{body_text[:200]!r}")
        except Exception as e:
            log(f"reload 失败：{e}")

    # 截图
    try:
        page.screenshot(path="bas_ide_after_open.png", full_page=True)
        log("已保存截图：bas_ide_after_open.png")
    except Exception:
        pass

    # 6. 如果还在 manager，再强制跳一次
    current = page.url
    if "index.html" in current or ("ws-manager" in current and "theia-workspaces" not in current):
        log("仍在 Manager，强制跳转 workspace_url...")
        try:
            page.goto(workspace_url, wait_until="domcontentloaded", timeout=180000)
            page.wait_for_timeout(30000)
        except Exception as e:
            log(f"强制跳转提示：{e}")

    # 7. 打开 Terminal
    open_terminal_and_activate(page)

    # 8. 最终保持
    log("额外保持页面打开 45 秒，确保节点完全激活...")
    page.wait_for_timeout(45000)

    try:
        page.screenshot(path="bas_ide_final.png", full_page=True)
        log("已保存最终截图：bas_ide_final.png")
    except Exception:
        pass

    log(f"Workspace 最终页面：{page.url}")
    log("Workspace 访问完成，节点激活流程已执行！")
    return True


# ============================================================
# 主程序
# ============================================================

def main():

    log("==========================================")
    log(" SAP BAS Dev Space Keep Alive")
    log("==========================================")

    check_environment()

    log(f"BAS URL      : {BAS_URL}")
    log(f"Dev Space    : {DEVSPACE_NAME}")
    log(f"Dev Space ID : {DEVSPACE_ID}")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--window-size=1366,768"
            ]
        )

        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            ignore_https_errors=True
        )

        page = context.new_page()

        try:

            if not login(page):
                log("登录失败，任务结束。")
                sys.exit(1)

            jwt = get_jwt(context)

            if not jwt:
                log("获取 JWT 失败。")
                sys.exit(1)

            log("JWT 获取成功。")

            workspace = get_workspace(context, jwt)

            if not workspace:
                sys.exit(1)

            status = get_status(workspace)
            log(f"{DEVSPACE_NAME} 当前状态：{status}")

            if status == "STOPPED":
                log("检测到 Dev Space 已停止。")
                success = start_workspace(context, jwt, workspace)
                if not success:
                    sys.exit(1)
                workspace = wait_until_running(context, jwt)
                if not workspace:
                    sys.exit(1)

            elif status in ["STARTING", "CREATING"]:
                log("Dev Space 正在启动。")
                workspace = wait_until_running(context, jwt)
                if not workspace:
                    sys.exit(1)

            elif status in ["RUNNING", "STARTED"]:
                log("Dev Space 已经处于 RUNNING。")

            else:
                log(f"未知 Dev Space 状态：{status}")

            workspace = get_workspace(context, jwt)
            if not workspace:
                sys.exit(1)

            final_status = get_status(workspace)
            log(f"最终状态：{final_status}")

            if final_status not in ["RUNNING", "STARTED"]:
                log("Dev Space 最终没有进入 RUNNING。")
                sys.exit(1)

            open_workspace(page, context, jwt, workspace)

            log("==========================================")
            log(" Keep Alive 执行成功")
            log(f" Dev Space : {DEVSPACE_NAME}")
            log(" 状态      : RUNNING")
            log(" Workspace : 已访问且已触发节点联动")
            log("==========================================")

        except Exception as e:

            log("程序发生异常：")
            log(str(e))

            try:
                page.screenshot(path="bas_error.png", full_page=True)
            except Exception:
                pass

            sys.exit(1)

        finally:

            context.close()
            browser.close()


if __name__ == "__main__":
    main()

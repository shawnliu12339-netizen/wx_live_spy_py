# 微信视频号直播弹幕抓取工具（Python 版）

这是 [wxlivespy](https://github.com/fire4nt/wxlivespy) 项目的 Python 精简实现，使用 Playwright 自动化浏览器，拦截微信视频号管理后台的网络请求，实时获取直播间的弹幕、礼物、点赞等事件。

## 功能特性

- ✅ 实时获取直播间弹幕（评论）
- ✅ 监听礼物打赏信息
- ✅ 捕获用户进入直播间事件
- ✅ 记录点赞和用户等级提升
- ✅ 自动保持登录状态
- ✅ 扫码登录后自动跳转到直播控制台

## 原理说明

本工具通过 Playwright 控制 Chromium 浏览器，打开微信视频号管理后台（`https://channels.weixin.qq.com/platform/live/liveBuild`），拦截所有包含 `mmfinderassistant-bin/live/msg` 的 HTTP 响应，解析其中的 JSON 数据，提取出弹幕、礼物等事件信息。

**核心流程：**
1. 启动 Chromium 浏览器并打开微信视频号管理后台
2. 用户扫码登录微信账号
3. 监听所有网络请求，筛选出 `live/msg` 接口
4. 解析响应中的 `msgList`（弹幕、进入）和 `appMsgList`（礼物、点赞）
5. 在终端实时打印解析后的事件

## 安装依赖

## Windows 安装包

仓库已提供 Windows x64 安装包构建配置。安装包会内置 Python 程序、Playwright 和 Chromium，最终用户不需要单独安装 Python 或浏览器。

### 使用 GitHub Actions 构建（推荐）

1. 将代码推送到 GitHub。
2. 打开仓库的 **Actions → Build Windows installer → Run workflow**。
3. 构建完成后，在该任务的 Artifacts 中下载 `WXLiveSpy-Windows-Installer`。
4. 解压并运行 `WXLiveSpy-Setup-x64.exe`。

推送 `v1.0.0` 形式的标签时，安装包也会自动附加到对应的 GitHub Release。

### 在 Windows 本机构建

需要 Windows 10/11 x64、Python 3.9+ 和 [Inno Setup 6](https://jrsoftware.org/isinfo.php)。在 PowerShell 中运行：

```powershell
.\build_windows.ps1
```

生成的安装包位于 `installer\Output\WXLiveSpy-Setup-x64.exe`。如果未安装 Inno Setup，仍会生成 `dist\WXLiveSpy` 免安装目录。

安装后从桌面或开始菜单启动。首次运行会显示 Chromium 窗口，需要微信扫码；登录数据保存在 `%LOCALAPPDATA%\WXLiveSpy\browser-profile`。

> Windows Defender/SmartScreen 可能提示未知发布者，这是未使用代码签名证书造成的。公开分发时建议对安装包签名。

## 开发环境安装依赖

### 1. 安装 Python 依赖

```bash
pip install playwright httpx
```

### 2. 安装 Playwright 浏览器

```bash
playwright install chromium
```

## 使用方法

### 基础用法

```bash
python wx_live_spy.py
```

运行后会弹出 Chromium 浏览器窗口，显示微信视频号管理后台的登录页面：

1. 使用微信扫描页面上的二维码登录
2. 登录成功后，脚本会自动跳转到直播控制台
3. 打开你的直播间，终端会实时显示弹幕和礼物信息

### 命令行参数

```bash
python wx_live_spy.py [选项]
```

**可用选项：**

- `--spy-url URL`：指定微信视频号后台地址（默认：`https://channels.weixin.qq.com/platform/live/liveBuild`）
- `--user-data-dir PATH`：指定 Chromium 用户数据目录，用于保存登录状态（默认：`~/.wx_live_spy`）
- `--headless`：以无头模式运行（不显示浏览器窗口，需要已登录）
- `--verbose`：输出详细的调试日志

**示例：**

```bash
# 使用自定义用户数据目录
python wx_live_spy.py --user-data-dir ~/my_wx_data

# 开启详细日志
python wx_live_spy.py --verbose

# 无头模式运行（需要先扫码登录过一次）
python wx_live_spy.py --headless
```

## 输出示例

运行后，终端会实时显示类似以下的事件信息：

```
2024-12-02 10:30:15 INFO 打开微信视频号后台: https://channels.weixin.qq.com/platform/live/liveBuild
2024-12-02 10:30:18 INFO 请扫码登录并进入直播间，终端会实时显示弹幕。
2024-12-02 10:31:05 INFO [comment] 张三: 主播好！
2024-12-02 10:31:08 INFO [enter] 李四: 李四进入直播间
2024-12-02 10:31:12 INFO [gift] 王五 -> gift_12345 x1 (worth 10)
2024-12-02 10:31:15 INFO [like] 赵六 点赞
2024-12-02 10:31:20 INFO [combogift] 孙七 -> gift_67890 x5 (worth None)
```

## 事件类型说明

| 事件类型 | 说明 | 包含信息 |
|---------|------|---------|
| `comment` | 用户发送弹幕评论 | 昵称、内容 |
| `enter` | 用户进入直播间 | 昵称 |
| `gift` | 用户送礼物 | 昵称、礼物ID、数量、价值（微信豆） |
| `combogift` | 连击礼物 | 昵称、礼物ID、连击数 |
| `like` | 用户点赞 | 昵称 |
| `levelup` | 用户等级提升 | 昵称、原等级、新等级 |

## 注意事项

1. **登录状态保存**：首次运行需要扫码登录，登录信息会保存在 `--user-data-dir` 指定的目录中，下次运行时会自动复用
2. **需要进入直播间**：扫码登录后，需要在浏览器中点击进入你的直播间，才能开始抓取弹幕
3. **自动跳转**：如果登录后被重定向到其他页面，脚本会每 5 秒检查一次并自动跳回直播控制台
4. **网络稳定性**：需要保持网络连接稳定，否则可能丢失部分事件
5. **仅限个人使用**：请遵守微信平台的使用条款，仅用于个人学习和研究

## 常见问题

### Q: 为什么扫码后没有弹幕显示？

A: 请确保：
1. 已经在浏览器中进入了直播间（不是只登录后台）
2. 直播间确实有用户在发弹幕
3. 查看终端是否有错误日志（使用 `--verbose` 参数）

### Q: 如何在服务器上运行？

A: 服务器上运行需要：
1. 先在本地扫码登录一次，将 `~/.wx_live_spy` 目录复制到服务器
2. 在服务器上使用 `--headless` 参数运行
3. 确保服务器安装了必要的系统依赖（如 X11 库）

### Q: 能否获取历史弹幕？

A: 不能。本工具只能实时抓取当前的弹幕，无法获取历史记录。

### Q: 抓取的数据能否保存到文件或数据库？

A: 当前版本只在终端打印。如需保存数据，可以：
1. 使用重定向：`python wx_live_spy.py > danmaku.log`
2. 修改代码，在 `_print_event` 方法中添加保存逻辑

## 与原项目的区别

| 特性 | 原项目（Electron） | Python 版 |
|-----|------------------|----------|
| 界面 | 有 GUI 界面 | 纯命令行 |
| 依赖 | Node.js + Electron | Python + Playwright |
| 功能 | 完整（包含转发、OpenID 映射等） | 精简版（仅核心抓取功能） |
| 体积 | 较大（~100MB） | 较小（~10MB） |
| 适用场景 | 桌面应用 | 脚本/服务器 |

## 技术栈

- **Python 3.7+**
- **Playwright**：浏览器自动化框架
- **asyncio**：异步 I/O 支持

## 许可证

MIT License

## 相关链接

- 原项目（Electron 版）：https://github.com/fire4nt/wxlivespy
- Playwright 文档：https://playwright.dev/python/

## 贡献

欢迎提交 Issue 和 Pull Request！

## 免责声明

本工具仅供学习和研究使用，请勿用于商业用途或违反微信平台规则的行为。使用本工具产生的任何后果由使用者自行承担。

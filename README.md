<p align="center">
  <img src="./frontend/public/first.png" alt="Open-Anti-Browser" width="100%">
</p>

# Open-Anti-Browser

[English README](./README_EN.md)

> 本构建是 [Wtcity22/Open-Anti-Browser](https://github.com/Wtcity22/Open-Anti-Browser) 的 fork，由 ShengSoft-Tech 维护与构建发布。功能与上游保持一致，并保留原项目的开源声明与内核来源署名。

Open-Anti-Browser 是一个本地桌面端指纹浏览器管理器

它把两套可公开获取的指纹内核整理到同一个界面里，方便创建配置、管理代理、统一扩展、启动浏览器，以及通过本地 API 接入自动化流程

界面采用 iOS 风格设计，支持浅色和深色模式切换

<p align="center">
  <img src="./frontend/public/banner1.png" alt="Open-Anti-Browser banner 1" width="100%">
</p>

<p align="center">
  <img src="./frontend/public/banner2.png" alt="Open-Anti-Browser banner 2" width="100%">
</p>

## 功能概况

### 配置与指纹

- 支持 Chrome 和 Firefox 两套指纹内核
- 每个配置拥有独立用户目录，浏览器数据彼此隔离
- 支持按配置保存名称、分组、备注、代理、启动参数、启动网址
- Chrome 支持固定 `fingerprint id`、平台选择、语言与时区覆盖、CPU 线程模式、窗口尺寸等常用参数
- Firefox 支持语言与时区、字体系统、屏幕尺寸、WebGL、WebRTC、CPU 线程、额外指纹字段、指纹文件路径等常用参数
- 支持按 IP 自动解析语言与时区，并写入对应浏览器配置

### 代理与扩展

- 支持保存常用代理、连通性测试、批量分配代理
- 支持全局扩展管理，可分别管理 Chrome 和 Firefox 扩展
- 支持上传扩展包，也支持直接选择已有扩展文件夹
- 已启用的全局扩展会自动跟随对应内核启动
- 单个浏览器配置里可以单独禁用某些全局扩展

### 标签页工具

- 支持批量打开网址
- 支持把第一条网址直接打开在当前标签页，也可以全部作为新标签页打开
- 支持把其他窗口的当前标签页统一到主窗口网址
- 支持批量关闭当前标签页
- 支持批量关闭其他标签页
- 支持批量关闭空白标签页和新标签页

### 同步器

- 支持选择一个主控窗口和多个跟随窗口进行联动
- 支持同步页面跳转、点击、文本输入、滚动、键盘动作、鼠标轨迹
- 支持同步标签页与浏览器顶部操作，包括地址栏跳转、新建标签页、切换标签页、关闭标签页
- 支持启动时把主控当前网址同步给所有跟随窗口
- 支持显示窗口、统一大小、一键排列等多窗口管理操作
- 支持文本同步工具，包括清空内容、相同内容、随机数字、指定文本组
- 支持同步延迟设置、快捷键设置、同步范围开关

### API 与桌面体验

- 支持本地 API Key、后端 API 模式、接口文档页面
- 启动浏览器后会返回本地调试端口，方便接入自动化工具
- 支持按分组批量启动和停止浏览器
- 支持单实例运行、托盘最小化、明暗主题切换

## 下载

- 安装包发布页（本 fork）: [Releases](https://github.com/ShengSoft-Tech/Open-Anti-Browser/releases)
- 本 fork 源码: [ShengSoft-Tech/Open-Anti-Browser](https://github.com/ShengSoft-Tech/Open-Anti-Browser)
- 原始项目: [Wtcity22/Open-Anti-Browser](https://github.com/Wtcity22/Open-Anti-Browser)

## 联系我
- email: wtcity22@gmail.com
- tg: @NetOriginDev

## 交流群

欢迎加入 QQ 交流群，一起交流使用经验、反馈问题、分享自动化玩法

<p align="center">
  <img src="./frontend/public/qq.jpg" alt="Open-Anti-Browser QQ 交流群" width="260">
</p>

## 内核来源

### Chromium 148

- 项目: [adryfish/fingerprint-chromium](https://github.com/adryfish/fingerprint-chromium)
- 本项目内置版本: Chromium 148

### Firefox 151

- 项目: [LoseNine/firefox-fingerprintBrowser](https://github.com/LoseNine/firefox-fingerprintBrowser)
- 自动化库: [LoseNine/ruyipage](https://github.com/LoseNine/ruyipage)
- 本项目内置版本: Firefox 151

### 自动化接入

- Chrome 推荐: [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright)
- Firefox 推荐: [RuyiPage](https://github.com/LoseNine/ruyipage)

## 指纹能力对比

| 项目 | Chrome | Firefox |
| --- | --- | --- |
| 固定指纹标识 | 支持 `fingerprint id` | 通过 `fpfile` 管理 |
| 按 IP 自动解析语言与时区 | 支持 | 支持 |
| 平台选择 | Windows / macOS / Linux | 字体系统选择 |
| CPU 线程数 | 自动 / 手动 / 随机 | 自动 / 手动 / 随机 |
| 屏幕参数 | 启动窗口大小 | 自动 / 手动 / 随机屏幕尺寸 |
| WebRTC | 跟随代理与启动参数 | 自动 / 手动 / 随机 |
| WebGL | 依赖内核指纹实现 | 自动 / 手动 / 随机 |
| 启动参数 | 支持 | 支持 |
| 启动后打开网址 | 支持 | 支持 |
| 全局扩展 | 支持 | 支持 |

## Chrome 支持的主要配置

- 固定或重新生成 fingerprint id
- 按 IP 自动解析语言和时区
- 手动语言、Accept-Language、时区覆盖
- 平台选择
- CPU 线程数自动、手动、随机
- 关闭指定伪装模块
- 启动参数
- 启动窗口大小
- 启动后自动打开网址
- 配置级禁用全局扩展

## Firefox 支持的主要配置

- 按 IP 自动解析语言和时区
- 手动语言和时区覆盖
- 字体系统选择
- 屏幕尺寸自动、手动、随机
- WebGL 自动、手动、随机
- CPU 线程数自动、手动、随机
- WebRTC 自动、手动、随机
- 内置 WebRTC 屏蔽扩展
- 额外指纹字段写入
- 自定义指纹文件路径
- 启动参数
- 启动后自动打开网址
- 配置级禁用全局扩展

## 如何使用

### 1 创建浏览器配置

- 选择 Chrome 或 Firefox 内核
- 填写名称、分组、备注
- 选择代理或保持直连
- 调整对应内核的指纹参数
- 保存后即可启动

### 2 管理代理

- 在代理管理页面保存常用代理
- 可先做连通性测试
- 可把同一条代理批量分配给多个配置

### 3 管理扩展

- 在扩展管理页面分别上传 Chrome 和 Firefox 扩展
- 启用后会自动跟随同内核配置启动
- 单个配置里可以临时禁用指定扩展

### 4 通过本地 API 调用

- 在程序左侧打开 API 调用 页面查看本地地址和 API Key
- 在 API 文档 页面查看接口说明和示例
- 启动配置后，返回结果里会包含调试端口 `port`

## 自动化示例

### Chrome

Chrome 启动后会返回本地调试端口，推荐用 Patchright 按 CDP 方式接入

### Firefox

Firefox 启动后同样会返回端口，推荐用 RuyiPage 直接连接

## 源码与构建

- 项目源码默认公开
- 为了尽量减少商业滥用，README 不提供现成的源码构建步骤
- 公开仓库不提供安装包打包脚本和现成构建配置
- 如需自行研究，请根据源码结构自行处理

## 说明

- Releases 页面提供可直接安装的版本
- 源码仓库默认不包含内核大文件、构建产物、运行数据和本地测试缓存
- 如果你要自行修改界面，前端源码位于 `frontend/src`
- 如果你要扩展后端接口，主入口位于 `backend/main.py`

## 使用边界

- 本项目是开源项目，不进行任何收费
- 本项目仅用于本地开发、自动化调试、测试验证和合规研究
- 禁止将本项目用于非法活动、未授权访问、批量滥用平台规则或其他侵权行为
- 使用者需自行确认所在地区的法律法规以及目标平台的使用规则

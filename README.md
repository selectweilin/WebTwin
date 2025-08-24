# 网站提取器

![Website Extractor Banner](https://img.shields.io/badge/Website%20Extractor-Advanced-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 概述

网站提取器是一个强大的基于 Python 的工具，能够让您一键下载和归档整个网站。此应用程序可以从任何网站提取 HTML、CSS、JavaScript、图像、字体和其他资源，非常适合用于：

- 创建任何线上网站的像素级完美副本
- 使用真实的网站内容训练 AI 代理
- 研究网站结构和设计
- 提取 UI 组件以获取设计灵感
- 为研究目的归档网站内容
- 学习网站开发技术

该应用程序具有使用 Selenium 的高级渲染功能，能够正确地从现代 JavaScript 重度网站和单页应用程序中提取资源。

![App Architecture Overview](https://raw.githubusercontent.com/username/website-extractor/main/docs/app_architecture_overview.png)

## 功能特性

- **高级渲染**：使用 Selenium 和 Chrome WebDriver 渲染 JavaScript 重度网站
- **全面的资源提取**：下载 HTML、CSS、JavaScript、图像、字体等
- **元数据提取**：捕获网站元数据、OpenGraph 标签和结构化数据
- **UI 组件分析**：识别和提取头部、导航、卡片等 UI 组件
- **有序输出**：创建结构良好的 ZIP 文件，按类型组织资源
- **响应式设计**：适用于桌面和移动网站
- **CDN 支持**：处理来自各种 CDN 的资源
- **现代框架支持**：特别支持 React、Next.js、Angular 和 Tailwind CSS

## 高级应用场景

### 像素级完美网站副本

为学习、测试或灵感目的创建网站的精确复制品。高级渲染引擎确保甚至复杂的布局和 JavaScript 驱动的设计都能忠实地重现。

### AI 代理训练

提取网站以为您的 AI 代理创建高质量的训练数据：

- 将结构化内容输入 AI 模型，提高其对网站布局的理解
- 在真实的 UI 组件和设计模式上训练 AI 助手
- 为机器学习项目创建多样化的网站内容数据集

### Cursor IDE 集成

网站提取器与 Cursor IDE 无缝集成：

- 提取网站并直接在 Cursor 中打开进行代码分析
- 使用 Cursor 的 AI 助手编辑提取的代码
- 将组件作为您自己项目的参考
- 请求 Cursor 分析网站结构和样式，并将类似模式应用到您的工作中

### 设计灵感和参考

将提取的文件夹上传到您当前的项目中：

- 请求 Cursor 在构建新页面时参考其样式
- 研究专业 UI 实现
- 提取特定组件以在您自己的项目中重用
- 从生产网站学习现代 CSS 技术

## 安装

### 前置条件

- Python 3.7+
- Chrome/Chromium 浏览器（用于高级渲染）
- Git

### 使用 Cursor（推荐）

1. 克隆仓库：

   ```bash
   git clone https://github.com/sirioberati/WebTwin.git
   cd WebTwin
   ```

2. 在 Cursor IDE 中打开项目：

   ```bash
   cursor .
   ```

3. 创建虚拟环境（在 Cursor 的终端中）：

   ```bash
   python -m venv venv
   ```

4. 激活虚拟环境：

   - Windows 系统：`venv\Scripts\activate`
   - macOS/Linux 系统：`source venv/bin/activate`

5. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

### 手动安装

1. 克隆仓库：

   ```bash
   git clone https://github.com/sirioberati/WebTwin.git
   cd WebTwin
   ```

2. 创建虚拟环境：

   ```bash
   python -m venv venv
   ```

3. 激活虚拟环境：

   - Windows 系统：`venv\Scripts\activate`
   - macOS/Linux 系统：`source venv/bin/activate`

4. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

1. 激活您的虚拟环境（如果尚未激活）

2. 运行应用程序：

   ```bash
   python app.py
   ```

3. 打开浏览器并导航到：

   ```
   http://127.0.0.1:5001
   ```

4. 输入您要提取的网站的 URL

5. 对于 JavaScript 重度网站，勾选"使用高级渲染 (Selenium)"

6. 点击"提取网站"并等待下载完成

### 使用高级渲染

高级渲染选项使用 Selenium 和 Chrome WebDriver 来：

- 执行 JavaScript
- 渲染动态内容
- 滚动页面以触发懒加载
- 点击 UI 元素以显示隐藏内容
- 提取由 JavaScript 框架加载的资源

对于现代网站，特别是使用 React、Angular、Vue 或其他 JavaScript 框架构建的网站，推荐使用此选项。

### 与 Cursor IDE 配合使用

提取网站后：

1. 将下载的文件解压到目录中
2. 使用 Cursor IDE 打开：

   ```bash
   cursor /path/to/extracted/website
   ```

3. 探索代码结构和资源
4. 使用类似以下提示让 Cursor AI 分析代码：
   - "解释这个网站的 CSS 结构"
   - "我如何在我的项目中实现类似的英雄区块？"
   - "分析这个导航组件并为我的 React 应用创建一个类似的组件"

## AI 代理集成

WebTwin 与 AI 代理结合使用时可以成为强大的工具，能够实现复杂的代码分析、设计提取和内容重用工作流程。

### 与 Cursor AI 集成

Cursor 的 AI 功能可以通过 WebTwin 的提取能力得到增强：

1. **提取和修改工作流程**：

   ```
   WebTwin → 提取网站 → 在 Cursor 中打开 → 请求 AI 修改
   ```

   示例提示：

   - "将这个着陆页转换为使用 Tailwind CSS 而不是 Bootstrap"
   - "重构这个 JavaScript 代码以使用 React hooks"
   - "简化这个复杂的 CSS 布局，同时保持相同的视觉外观"

2. **组件库创建**：

   ```
   WebTwin → 提取多个网站 → 在 Cursor 中打开 → AI 驱动的组件提取
   ```

   示例提示：

   - "从这些网站中提取所有按钮样式并创建统一的组件库"
   - "分析这些导航模式并创建最佳实践实现"

3. **从生产代码学习**：

   ```
   WebTwin → 提取复杂网站 → Cursor AI 分析 → 生成教程
   ```

   示例提示：

   - "解释这个网站如何实现其响应式设计策略"
   - "向我展示这个动画效果的工作原理并帮我实现类似的效果"

### 与 OpenAI Assistants API 和 Agent SDK 集成

WebTwin 可以与 OpenAI Assistants API 和 Agent SDK 集成，创建专门的 AI 代理：

1. **设置网站分析代理**：

   ```python
   from openai import OpenAI

   client = OpenAI(api_key="your-api-key")

   # 创建专门用于网站设计分析的助手
   assistant = client.beta.assistants.create(
       name="WebDesignAnalyzer",
       instructions="您分析由 WebTwin 提取的网站并提供设计见解。",
       model="gpt-4-turbo",
       tools=[{"type": "file_search"}]
   )

   # 上传提取的网站文件
   file = client.files.create(
       file=open("extracted_website.zip", "rb"),
       purpose="assistants"
   )

   # 创建包含文件的会话
   thread = client.beta.threads.create(
       messages=[
           {
               "role": "user",
               "content": "分析这个网站的设计模式和组件结构",
               "file_ids": [file.id]
           }
       ]
   )

   # 在会话上运行助手
   run = client.beta.threads.runs.create(
       thread_id=thread.id,
       assistant_id=assistant.id
   )
   ```

2. **创建网站转换管道**：

   ```
   WebTwin → 提取网站 → OpenAI 代理处理 → 生成新代码
   ```

3. **构建网站设计评判代理**：

   - 将 WebTwin 提取的内容提供给训练有素的 AI 代理以评估设计原则
   - 获得关于可访问性、可用性和视觉设计的详细反馈

### 高级代理工作流程

将 WebTwin 与 AI 代理结合用于高级工作流程：

1. **跨网站设计模式分析**：

   - 提取同一行业的多个网站
   - 使用 AI 识别常见模式和最佳实践
   - 生成行业标准方法报告

2. **自动化组件库生成**：

   - 提取多个网站
   - 使用 AI 识别和分类 UI 组件
   - 生成带有文档的统一组件库

3. **SEO 和内容策略分析**：

   - 提取内容丰富的网站
   - 使用 AI 分析内容结构、元数据和关键词使用
   - 生成 SEO 建议和内容策略见解

4. **竞争分析**：

   - 提取竞争对手网站
   - 使用 AI 比较功能、UX 模式和技术实现
   - 生成包含优势和劣势的竞争分析报告

## 架构

应用程序采用模块化架构设计，注重灵活性和性能：

```
┌───────────────────────────────────────────────────────────────────┐
│                    网站提取器应用程序                                │
└───────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌───────────────────────────────────────────────────────────────────┐
│                           Flask Web 服务器                         │
└───────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌───────────────────────────────────────────────────────────────────┐
│                      提取核心处理模块                                │
├───────────────┬──────────────────┬──────────────────┬─────────────┤
│  HTTP 客户端  │ Selenium 渲染器   │  内容解析器       │ 资源保存器   │
│ (requests)    │ (WebDriver)       │ (BeautifulSoup)  │ (Zip)       │
└───────────────┴──────────────────┴──────────────────┴─────────────┘
```

### 数据流

```
┌──────────┐    URL     ┌──────────┐  HTML 内容     ┌──────────────┐
│  用户    │───────────▶│ 提取器   │───────────────▶│ HTML 解析器   │
└──────────┘            └──────────┘                └──────────────┘
                             │                             │
                   渲染选项  │                             │ 资源 URL
                             │                             │
                             ▼                             ▼
                      ┌──────────┐                  ┌──────────────┐
                      │ Selenium │                  │ 资源         │
                      │ WebDriver│                  │ 下载器       │
                      └──────────┘                  └──────────────┘
                             │                             │
                     渲染后  │                      资源   │
                       HTML  │                             │
                             ▼                             ▼
                      ┌──────────────────────────────────────────┐
                      │            ZIP 文件创建器                │
                      └──────────────────────────────────────────┘
                                          │
                                          ▼
                      ┌──────────────────────────────────────────┐
                      │      文件下载响应给用户                    │
                      └──────────────────────────────────────────┘
```

### 关键组件

1. **Flask Web 服务器**：提供用户界面并处理 HTTP 请求
2. **HTTP 客户端**：使用 Requests 库发出请求以获取网站内容
3. **Selenium 渲染器**：用于 JavaScript 渲染和动态内容的可选组件
4. **内容解析器**：使用 BeautifulSoup 分析 HTML 以提取资源和结构
5. **资源下载器**：下载所有发现的资源，具有复杂的重试逻辑
6. **ZIP 创建器**：将所有内容打包成有组织的可下载归档文件

### 处理阶段

1. **URL 提交**：用户提供 URL 和渲染选项
2. **内容获取**：获取 HTML 内容（是否使用 JavaScript 渲染）
3. **结构分析**：解析和分析 HTML 以获取资源和组件
4. **资源发现**：识别和分类所有链接的资源
5. **并行下载**：使用优化的并发请求下载资源
6. **组织和打包**：将文件组织并压缩成 ZIP 归档文件

有关更详细的技术信息，请参阅 [app_architecture.md](app_architecture.md)。

## 限制

- 某些网站实施了反爬虫措施，可能会阻止提取
- 需要身份验证的内容可能无法访问
- 非常大的网站可能会超时或需要多次提取尝试
- 某些特定于 CDN 的 URL 格式可能无法下载（特别是那些带有转换参数的）

## 许可证

此项目在 MIT 许可证下授权 - 有关详细信息，请参阅 [LICENSE](LICENSE) 文件。

## 作者

由 Sirio Berati 创建

- Instagram: [@heysirio](https://instagram.com/heysirio)
- Instagram: [@siriosagents](https://instagram.com/siriosagents)

## 贡献

欢迎贡献！请随时提交 Pull Request。

1. Fork 仓库
2. 创建您的功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m '添加一些令人惊喜的功能'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

## 致谢

- 此项目使用 [Flask](https://flask.palletsprojects.com/) 作为 Web 框架
- [Selenium](https://www.selenium.dev/) 用于高级渲染
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) 用于 HTML 解析
- 所有使此项目成为可能的开源库

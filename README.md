# 个人财务小助手

一个可定制、本地运行的个人财务分析工具。支持**微信和支付宝账单**，通过用户自定义分类规则自动归类支出，生成可视化报表，并提供超支提醒、多用户数据隔离、在线规则编辑、预算设置、交互式图表等丰富功能。所有数据安全存储在本地 MySQL 数据库中，隐私无忧。

---

## 📌 项目背景

市面上的记账软件分类规则固定，无法识别个性化消费（如“恒星邦办”属于居住，“抖音电商”属于购物）。手动记账繁琐难坚持。本项目旨在提供一个 **懂你、私密、可扩展** 的财务分析方案。

---

## ✨ 核心功能

✅ **多平台账单支持**  
- 微信账单（Excel 格式）自动导入清洗  
- 支付宝账单（CSV 格式）自动导入清洗  
- 支持同时上传多个文件，自动合并去重  

✅ **用户自定义分类**  
- 通过 JSON 文件配置关键词，自由定义支出类别（如“居住”、“餐饮”）  
- 大小写不敏感，支持子串匹配，未匹配的交易自动归入“其他”  

✅ **自动分类与统计**  
- 基于规则对每笔支出打标签，输出月度汇总  
- 支持多月份数据合并分析  

✅ **可视化报表**  
- 生成包含明细、月度汇总、超支统计的 Excel 报表  
- 内嵌饼图（图例含金额）、月度趋势折线图、月度柱状图、超支条形图  

✅ **网页端交互式图表**  
- 使用 ECharts 实现可交互的饼图、趋势图、超支条形图，鼠标悬停显示详情  
- 上传后直接在网页上预览图表，无需下载  

✅ **智能超支提醒**  
- 按月度设置预算（支持默认预算），自动检查超支  
- 在 Excel 报表中标红超支单元格  
- 输出超支明细 CSV 文件  

✅ **多用户与数据隔离**  
- 注册/登录功能（密码加密），每个用户只能查看自己的账单数据  
- 数据安全存储于 MySQL 数据库  

✅ **仪表盘首页**  
- 展示用户信息、总收支、交易笔数、报表数量  
- 当月支出概览与超支状态  
- 最近5笔支出记录，快速导航至各功能  

✅ **报表历史管理**  
- 每个用户可查看自己生成的所有报表  
- 支持下载和删除报表（物理文件+数据库记录）  

✅ **在线规则编辑**  
- 在网页端直接修改分类规则（`category_rules.json`），即时生效  
- 支持 JSON 格式校验，错误提示  

✅ **在线预算编辑**  
- 在网页端直接修改月度预算（`budget.json`），格式校验  
- 未设置的月份自动使用默认预算  

✅ **一键运行**  
- 命令行版：`python src/main.py` 完成导入、分类、报表全流程  
- Web 版：`python web_app/app.py` 启动本地服务，浏览器访问  

---

## 🛠️ 技术栈

- **后端**：Python 3.8+，Flask 框架  
- **数据库**：MySQL 8.0，SQLAlchemy ORM（含 Flask-SQLAlchemy）  
- **数据处理**：Pandas，PyArrow（Parquet 格式）  
- **可视化**：ECharts（前端交互图表），Matplotlib + OpenPyXL（Excel 报表图表）  
- **前端**：HTML，Jinja2 模板，Bootstrap 5，ECharts JS  
- **用户认证**：Flask-Login，Flask-Bcrypt  
- **表单处理**：Flask-WTF，WTForms  
- **配置文件**：JSON  
- **版本控制**：Git  

模块化设计，代码清晰易扩展，欢迎 Fork 或 PR。

---

## 📁 项目结构

```
personal_finance/
├── config/                       # 配置文件
│   ├── budget.json                # 月度预算（用户可在线编辑）
│   └── category_rules.json        # 分类规则（用户可在线编辑）
├── data/
│   ├── raw/                       # 原始账单文件（用户放置）
│   └── processed/                  # 清洗后的中间数据（自动生成）
├── src/                           # 核心处理模块
│   ├── import_data.py             # 导入与清洗（微信/支付宝）
│   ├── classify.py                # 基于规则的分类
│   ├── report.py                  # 报表生成与图表绘制（Excel）
│   ├── alert.py                   # 超支检查与标记
│   └── main.py                    # 命令行一键运行入口
├── web_app/                       # Web 应用目录
│   ├── app.py                      # Flask 主程序
│   ├── templates/                   # HTML 模板
│   │   ├── base.html                # 基础模板（导航栏、闪现消息）
│   │   ├── dashboard.html           # 用户仪表盘首页
│   │   ├── index.html               # 上传页面
│   │   ├── result.html              # 结果页面（交互式图表）
│   │   ├── history.html             # 历史查询页面（含超支条形图）
│   │   ├── reports_list.html        # 我的报表列表（带删除）
│   │   ├── edit_rules.html          # 编辑分类规则
│   │   ├── edit_budget.html         # 编辑预算
│   │   ├── login.html               # 登录页面
│   │   └── register.html            # 注册页面
│   └── static/                      # （可选）CSS/JS 文件
├── output/                         # 生成的报表、超支记录
├── .gitignore                      # 忽略临时文件
├── requirements.txt                # 依赖包
└── README.md                       # 本文件
```

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/liguojing112/personal-finance-assistant.git
cd personal-finance-assistant
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
pip install flask-login flask-bcrypt flask-wtf email-validator  # Web 版额外依赖
```

### 3. 配置 MySQL 数据库

- 安装 MySQL 8.0，启动服务。
- 创建数据库（在 MySQL 命令行中执行）：
  ```sql
  CREATE DATABASE finance_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  ```
- 修改 `web_app/app.py` 中的数据库连接密码（第 20 行左右）：
  ```python
  app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:你的密码@localhost/finance_db'
  ```
- 创建数据表（在 `web_app` 目录下运行 Python）：
  ```python
  from app import app, db
  with app.app_context():
      db.create_all()
  ```

### 4. 配置分类规则（可选）

编辑 `config/category_rules.json`，或登录 Web 后在“分类规则”页面在线编辑。示例：

```json
{
    "居住": ["水电费", "恒星邦办", "康佳滚筒"],
    "餐饮": ["便利店", "农夫山泉", "肉夹馍", "水果"],
    "购物": ["抖音电商", "拼多多"],
    "社交": ["转账", "红包"],
    "学习": ["打印", "复印"],
    "其他": []
}
```

### 5. 配置预算（可选）

编辑 `config/budget.json`，或登录 Web 后在“编辑预算”页面在线编辑。未设置的月份将使用 `alert.py` 中的 `DEFAULT_BUDGET`。

```json
{
    "2026-01": {
        "总预算": 800,
        "居住": 200,
        "餐饮": 300,
        "购物": 150,
        "社交": 100,
        "学习": 30,
        "其他": 50
    }
}
```

### 6. 运行 Web 应用

```bash
cd web_app
python app.py
```

访问 `http://127.0.0.1:5000`，注册账号并登录。

### 7. 上传账单

- 从微信导出账单：我 → 服务 → 钱包 → 账单 → 下载 → 用于个人对账（Excel 格式）。
- 从支付宝导出账单：我的 → 账单 → 开具交易流水证明 → 用于个人对账 → 发送到邮箱，下载 CSV 文件。
- 在网页上同时选择多个文件（支持 `.xlsx` 和 `.csv`），点击“上传并分析”。

### 8. 查看结果

- 网页上会立即显示交互式饼图（图例含金额）和月度趋势图（可悬停）。
- 点击“下载详细报表”可获取包含所有明细、汇总和超支标记的 Excel 文件。
- 在“历史查询”页面可按日期筛选记录，并查看各类别累计超支条形图。
- 在“我的报表”页面可下载或删除历史生成的报表。
- 在“分类规则”和“编辑预算”页面可随时调整配置。

---

## 📸 效果展示

> 可在此处添加截图，如仪表盘首页、上传页、结果页（交互式图表）、历史查询页（超支条形图）、我的报表页（带删除）、编辑规则页等。  
> （用户可自行截图替换）

---

## 🧭 未来计划

- [ ] 增加机器学习辅助分类（当规则未覆盖时）
- [ ] 支持多账单合并（如多个微信账号）
- [ ] 增加年报表与同比分析
- [ ] 部署到云服务器，支持在线使用
- [ ] 添加数据导出功能（CSV/PDF）

---

## 🤝 贡献指南

欢迎提交 Issue 或 Pull Request。如果你希望增加新功能，请先开 Issue 讨论。

---

## 📄 许可证

MIT License

---

**Happy budgeting!** 🧾
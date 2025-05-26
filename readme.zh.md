# 中行外汇汇率监控

一个用于监控中国银行的外汇汇率的 Python 应用程序，当汇率满足特定条件时发送邮件通知。该应用程序通过 GitHub Actions 每 10 分钟自动运行一次。

## 功能特点

- 🔄 自动监控中国银行外汇汇率
- 📊 支持同时监控多种货币
- 🎯 可配置不同类型汇率的告警条件：
  - 现汇买入价
  - 现钞买入价
  - 现汇卖出价
  - 现钞卖出价
- 📧 当汇率满足条件时发送邮件通知
- 💬 **邮件回复命令** 快速调整监控阈值
- 🔄 通过 GitHub Actions 每 10 分钟运行一次
- 📝 详细的日志记录，便于监控和调试
- 🔄 通过 git 提交自动保存配置更改

## 使用方法

1. Fork 本仓库
2. 在仓库的 Secrets 中设置相关配置（详细信息参见[配置设置](#3-相关配置)的**第 2 部分**）
3. 在 `config.yaml` 中设置你想监控的币种和汇率条件
4. 启用仓库的 Actions
5. 当汇率满足设定的条件时，设定的邮箱将会收到邮件通知。

## 邮件回复命令

🆕 **新功能**：现在可以通过回复告警邮件来快速调整监控阈值！

当您收到汇率告警邮件时，可以在回复中使用特定命令来自动调整设定值。系统将会：

1. 解析您回复中的调整命令
2. 自动更新配置
3. 将更改提交到仓库
4. 发送确认邮件

### 快速命令

回复任何告警邮件时使用以下命令：

```
ADJUST USD spot_buying_rate max 740
SET GBP spot_selling_rate min 920 max 950
REMOVE JPY spot_selling_rate min
```

### 可用命令

- **ADJUST**：修改现有设定值，不删除其他条件
- **SET**：替换指定汇率类型的所有条件
- **REMOVE**：删除特定条件（最小值或最大值）

### 使用示例

**提高美元阈值：**

```
ADJUST USD spot_buying_rate max 740
```

**设置英镑综合监控：**

```
SET GBP spot_selling_rate min 920 max 950
```

**在一封邮件中进行多项调整：**

```
ADJUST USD spot_buying_rate max 740
ADJUST GBP spot_selling_rate min 925
REMOVE JPY spot_selling_rate max
```

详细的邮件回复命令文档请参见 [EMAIL_REPLY_COMMANDS.md](EMAIL_REPLY_COMMANDS.md)。

## 本地调试

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/exchange-rate-monitor.git
cd exchange-rate-monitor
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 相关配置

1. 本地开发时，更新 `config.yaml` 配置：

   **注意：请不要将邮箱密码等信息上传到仓库，避免泄露个人隐私。**

   ```yaml
   email:
     smtp_server: smtp.gmail.com
     smtp_port: 587
     sender_email: your-email@gmail.com
     sender_password: your-app-password # 仅用于本地开发
     recipient_email: recipient@example.com

   currencies:
     - name: 美元
       code: USD
       conditions:
         spot_buying_rate: # 现汇买入价
           min: 725.0 # 最低价，低于此价会发送邮件
           max: 733.0 # 最高价，高于此价会发送邮件
         spot_selling_rate: # 现汇卖出价
           min: 728.0
           max: 750.0
   ```

2. 生产环境部署时，需要设置 Repository Secrets：

   - 进入仓库的 Settings > Secrets
   - 添加以下 Secrets 变量：
     - `EMAIL_SMTP_SERVER`: SMTP 服务器地址（如 smtp.gmail.com）
     - `EMAIL_SMTP_PORT`: SMTP 端口（如 587）
     - `EMAIL_SENDER`: 发件人邮箱地址
     - `EMAIL_PASSWORD`: 邮箱密码或应用专用密码
     - `EMAIL_RECIPIENT`: 收件人邮箱地址
     - `EMAIL_IMAP_SERVER`: IMAP 服务器地址（如 imap.gmail.com）- 用于邮件回复功能
     - `EMAIL_IMAP_PORT`: IMAP 端口（如 993）- 用于邮件回复功能

### 4. 运行应用

```bash
python exchange_monitor.py
```

## 配置指南

### 货币配置

在 `config.yaml` 中添加需要监控的货币：

```yaml
currencies:
  - name: 美元 # 货币名称必须与中行网站一致
    code: USD
    conditions:
      spot_buying_rate: # 现汇买入价
        min: 725.0
        max: 733.0
      spot_selling_rate: # 现汇卖出价
        min: 728.0
        max: 750.0
      cash_buying_rate: # 现钞买入价
        min: 725.0
        max: 733.0
      cash_selling_rate: # 现钞卖出价
        min: 728.0
        max: 750.0
```

### 邮箱配置

对于使用两步验证和专用密码的邮箱（如 Gmail），需要进行以下配置：

1. 开启两步验证
2. 生成应用专用密码
3. 在配置中使用应用专用密码

## 日志记录

脚本会记录重要事件和错误，以帮助监控和调试：

- 汇率检查状态
- 邮件发送通知
- 获取或解析汇率时的错误
- 配置问题

## 参与贡献

1. Fork 本仓库
2. 创建 feature 分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m '添加某个特性'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 许可证

> 中国银行外汇牌价网页声明：
>
> 1. 本汇率表单位为 100 外币换算人民币，仅供参考，客户办理结/购汇业务时，应以中国银行网上银行、手机银行、智能柜台或网点柜台实际交易汇率为准，对使用该汇率表所导致的结果，中国银行不承担任何责任；
> 2. 未经中国银行许可，不得以商业目的转载本汇率表的全部或部分内容，如需引用相关数据，应注明来源于中国银行；
> 3. 中国银行外汇牌价业务系统于 2011 年 10 月 30 日进行了升级，本汇率表原有的"卖出价"细分为"现汇卖出价"和"现钞卖出价"，此前各货币的"卖出价"均显示在"现汇卖出价"项下。
> 4. 具体兑换币种以当地中国银行实际开办币种为准，客户可前往当地中国银行网点咨询或致电 95566。

根据该网页要求，本项目采用知识共享署名-非商业性使用-相同方式共享 4.0 国际许可协议（CC BY-NC-SA 4.0）-
详见 LICENSE 文件。这意味着您可以自由使用和修改此代码用于非商业目的，但必须提供适当的署名，
并在相同的许可证下共享您的修改。

## 免责声明

本工具数据来源于中国银行外汇牌价网页，仅用于教育和个人用途。请确保遵守中国银行的服务条款和数据使用政策。

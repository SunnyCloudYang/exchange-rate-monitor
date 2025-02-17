# Exchange Rate Monitor

[中文版](readme.zh.md)

A Python application that monitors Bank of China's exchange rates and sends email notifications when rates meet specified conditions. The application runs automatically every 10 minutes using GitHub Actions.

## Features

- 🔄 Automatically monitors exchange rates from Bank of China (中国银行)
- 📊 Supports monitoring multiple currencies simultaneously
- 🎯 Configurable alert conditions for different rate types:
  - Spot Buying Rate (现汇买入价)
  - Cash Buying Rate (现钞买入价)
  - Spot Selling Rate (现汇卖出价)
  - Cash Selling Rate (现钞卖出价)
- 📧 Email notifications when rates meet specified conditions
- 🔄 Runs every 10 minutes via GitHub Actions
- 📝 Detailed logging for monitoring and debugging

## Usage

1. Fork this repository
2. Create repository secrets for email configuration (See **part 2** of [configure settings](#3-configure-settings) for more details)
3. Update `config.yaml` with your monitoring settings
4. Enable GitHub Actions in your repository
5. Then sit back and relax! You will receive email notifications when exchange rates meet your conditions.

## Local Development

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/exchange-rate-monitor.git
cd exchange-rate-monitor
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Settings

1. For local development, update `config.yaml` with your settings:

   **Warning: DO NOT use local configuration in production environments to avoid exposing personal information.**

   ```yaml
   email:
   smtp_server: smtp.gmail.com
   smtp_port: 587
   sender_email: your-email@gmail.com
   sender_password: your-app-password # Only used for local development
   recipient_email: recipient@example.com

   currencies:
   - name: 美元 # USD
       code: USD
       conditions:
       spot_buying_rate:
           min: 700.0
           max: 750.0
       spot_selling_rate:
           min: 700.0
           max: 750.0
   ```

2. For production deployment, please set up GitHub Secrets:
   - Go to your repository's Settings > Secrets
   - Add the following secrets:
     - `EMAIL_SMTP_SERVER`: SMTP server address (e.g., smtp.gmail.com)
     - `EMAIL_SMTP_PORT`: SMTP port (e.g., 587)
     - `EMAIL_SENDER`: Your sender email address
     - `EMAIL_PASSWORD`: Your email password/app password
     - `EMAIL_RECIPIENT`: Recipient email address

### 4. Running the Application

```bash
python exchange_monitor.py
```

## Configuration Guide

### Currency Configuration

Add currencies to monitor in `config.yaml`:

```yaml
currencies:
  - name: 美元 # Currency name must match BOC's website
    code: USD
    conditions:
      spot_buying_rate: # 现汇买入价
        min: 700.0
        max: 750.0
      spot_selling_rate: # 现汇卖出价
        min: 700.0
        max: 750.0
      cash_buying_rate: # 现钞买入价
        min: 700.0
        max: 750.0
      cash_selling_rate: # 现钞卖出价
        min: 700.0
        max: 750.0
```

### Email Configuration

For emails with 2-factor authentication like Gmail:

1. Enable 2-factor authentication
2. Generate an App Password
3. Use the App Password in configuration

## Logging

The application logs important events and errors to help with monitoring and debugging:

- Successful rate checks
- Email notifications
- Errors in fetching or parsing rates
- Configuration issues

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

As required by the webpage, this project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International License - see the LICENSE file for details. This means you can freely use and
modify this code for non-commercial purposes, as long as you provide attribution and share
your changes under the same license.

## Disclaimer

This tool uses data from the Bank of China exchange rate webpage, and is for educational and personal use only. Please ensure you comply with Bank of China's terms of service and data usage policies when using this tool.

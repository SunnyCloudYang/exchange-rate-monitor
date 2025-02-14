import yaml
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from datetime import datetime
import sys
from typing import Dict, List, Optional
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ExchangeRateMonitor:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the exchange rate monitor with configuration."""
        self.config = self._load_config(config_path)
        self.url = self.config["monitoring"]["url"]

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file and override with environment variables."""
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)

            # Override email configuration with environment variables if they exist
            if os.getenv("EMAIL_SMTP_SERVER"):
                config["email"]["smtp_server"] = os.getenv("EMAIL_SMTP_SERVER")
            if os.getenv("EMAIL_SMTP_PORT"):
                config["email"]["smtp_port"] = int(os.getenv("EMAIL_SMTP_PORT"))
            if os.getenv("EMAIL_SENDER"):
                config["email"]["sender_email"] = os.getenv("EMAIL_SENDER")
            if os.getenv("EMAIL_PASSWORD"):
                config["email"]["sender_password"] = os.getenv("EMAIL_PASSWORD")
            if os.getenv("EMAIL_RECIPIENT"):
                config["email"]["recipient_email"] = os.getenv("EMAIL_RECIPIENT")

            return config
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            sys.exit(1)

    def _fetch_exchange_rates(self) -> Optional[str]:
        """Fetch the exchange rate page content."""
        try:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            response.encoding = "utf-8"
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch exchange rates: {e}")
            return None

    def _parse_rates(self, html_content: str) -> Dict[str, Dict[str, float]]:
        """Parse exchange rates from HTML content."""
        rates = {}
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            table = soup.find("table", {"align": "left"})

            for row in table.find_all("tr")[1:]:  # Skip header row
                cells = row.find_all("td")
                if len(cells) >= 8:
                    currency_name = cells[0].text.strip()
                    rates[currency_name] = {
                        "spot_buying_rate": self._parse_rate(cells[1].text),
                        "cash_buying_rate": self._parse_rate(cells[2].text),
                        "spot_selling_rate": self._parse_rate(cells[3].text),
                        "cash_selling_rate": self._parse_rate(cells[4].text),
                        "time": cells[7].text.strip(),
                    }

            return rates
        except Exception as e:
            logger.error(f"Failed to parse exchange rates: {e}")
            return {}

    def _parse_rate(self, rate_str: str) -> Optional[float]:
        """Parse rate string to float."""
        try:
            return float(rate_str.strip()) if rate_str.strip() else None
        except ValueError:
            return None

    def _check_conditions(self, currency_name: str, rates: dict) -> List[str]:
        """Check if rates meet alert conditions."""
        alerts = []
        currency_config = next(
            (c for c in self.config["currencies"] if c["name"] == currency_name), None
        )

        if not currency_config:
            return alerts

        conditions = currency_config["conditions"]
        current_rates = rates[currency_name]

        for rate_type, condition in conditions.items():
            current_rate = current_rates.get(rate_type)
            if current_rate is None:
                continue

            if condition["min"] and current_rate < condition["min"]:
                alerts.append(
                    f"{currency_name} {rate_type}: {current_rate} below minimum {condition['min']}"
                )
            elif condition["max"] and current_rate > condition["max"]:
                alerts.append(
                    f"{currency_name} {rate_type}: {current_rate} above maximum {condition['max']}"
                )

        return alerts

    def _send_email(self, subject: str, body: str):
        """Send email notification."""
        try:
            email_config = self.config["email"]

            msg = MIMEMultipart()
            msg["From"] = email_config["sender_email"]
            msg["To"] = email_config["recipient_email"]
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(
                email_config["smtp_server"], email_config["smtp_port"]
            ) as server:
                server.starttls()
                server.login(
                    email_config["sender_email"], email_config["sender_password"]
                )
                server.send_message(msg)

            logger.info("Alert email sent successfully")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    def monitor(self):
        """Main monitoring function."""
        logger.info("Starting exchange rate monitoring...")

        html_content = self._fetch_exchange_rates()
        if not html_content:
            return

        rates = self._parse_rates(html_content)
        if not rates:
            logger.error("No rates found in the HTML content")
            return

        all_alerts = []
        for currency in self.config["currencies"]:
            currency_name = currency["name"]
            if currency_name in rates:
                alerts = self._check_conditions(currency_name, rates)
                all_alerts.extend(alerts)
                logger.info(f"Rate for {currency_name}: {rates[currency_name]}")
            else:
                logger.info(f"No rate found for {currency_name}")

        if all_alerts:
            subject = (
                f"Exchange Rate Alert - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            body = "\n".join(all_alerts)
            self._send_email(subject, body)


if __name__ == "__main__":
    monitor = ExchangeRateMonitor()
    monitor.monitor()

import yaml
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from datetime import datetime, timedelta, timezone
import sys
from typing import Dict, List, Optional, Tuple
import os
import re
import json
from imapclient import IMAPClient
import email
from email.header import decode_header
from email_reply_parser import EmailReplyParser

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
            if os.getenv("EMAIL_IMAP_SERVER"):
                config["email"]["imap_server"] = os.getenv("EMAIL_IMAP_SERVER")
            if os.getenv("EMAIL_IMAP_PORT"):
                config["email"]["imap_port"] = int(os.getenv("EMAIL_IMAP_PORT"))

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

            alert_parts = []
            if "min" in condition and current_rate < condition["min"]:
                alert_parts.append(
                    f"""
                    <div style="color: #D32F2F; padding: 10px; margin: 10px 0; background-color: #FFEBEE; border-left: 4px solid #D32F2F;">
                        <h3 style="margin: 0;">🔔 Exchange Rate Alert - Below Minimum</h3>
                        <p style="margin: 10px 0;"><strong>Currency:</strong> {currency_name}</p>
                        <p style="margin: 10px 0;"><strong>Type:</strong> {rate_type}</p>
                        <p style="margin: 10px 0;"><strong>Current Rate:</strong> {current_rate:.2f}</p>
                        <p style="margin: 10px 0;"><strong>Minimum Threshold:</strong> {condition['min']:.2f}</p>
                        <p style="margin: 10px 0;"><strong>Status:</strong> BELOW minimum</p>
                        <p style="margin: 10px 0;"><strong>Time:</strong> {rates[currency_name]['time']}</p>
                    </div>
                    """
                )
            elif "max" in condition and current_rate > condition["max"]:
                alert_parts.append(
                    f"""
                    <div style="color: #2E7D32; padding: 10px; margin: 10px 0; background-color: #E8F5E9; border-left: 4px solid #2E7D32;">
                        <h3 style="margin: 0;">🔔 Exchange Rate Alert - Above Maximum</h3>
                        <p style="margin: 10px 0;"><strong>Currency:</strong> {currency_name}</p>
                        <p style="margin: 10px 0;"><strong>Type:</strong> {rate_type}</p>
                        <p style="margin: 10px 0;"><strong>Current Rate:</strong> {current_rate:.2f}</p>
                        <p style="margin: 10px 0;"><strong>Maximum Threshold:</strong> {condition['max']:.2f}</p>
                        <p style="margin: 10px 0;"><strong>Status:</strong> ABOVE maximum</p>
                        <p style="margin: 10px 0;"><strong>Time:</strong> {rates[currency_name]['time']}</p>
                    </div>
                    """
                )
            
            if alert_parts:
                alerts.extend(alert_parts)

        return alerts

    def _send_email(self, subject: str, body: str):
        """Send email notification."""
        try:
            email_config = self.config["email"]

            msg = MIMEMultipart()
            msg["From"] = email_config["sender_email"]
            msg["To"] = email_config["recipient_email"]
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "html", "utf-8"))

            # Use SSL by default for ports 465
            if email_config["smtp_port"] == 465:
                with smtplib.SMTP_SSL(
                    email_config["smtp_server"], email_config["smtp_port"]
                ) as server:
                    server.login(
                        email_config["sender_email"], email_config["sender_password"]
                    )
                    server.send_message(msg)
            else:
                # For other ports (like 587), use STARTTLS
                with smtplib.SMTP(
                    email_config["smtp_server"], email_config["smtp_port"]
                ) as server:
                    server.starttls()  # Enable TLS for all non-SSL connections
                    server.login(
                        email_config["sender_email"], email_config["sender_password"]
                    )
                    server.send_message(msg)

            logger.info("Alert email sent successfully")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    def _check_inbox_for_adjustments(self) -> List[Dict]:
        """Check inbox for setpoint adjustment emails."""
        adjustments = []
        try:
            email_config = self.config["email"]
            
            with IMAPClient(email_config["imap_server"], ssl=email_config.get("use_ssl", True)) as server:
                server.login(email_config["sender_email"], email_config["sender_password"])
                server.select_folder('INBOX')
                
                # Search for unread emails from the recipient (replies to our alerts)
                messages = server.search(['UNSEEN', 'FROM', email_config["recipient_email"]])
                
                for uid in messages:
                    raw_message = server.fetch([uid], ['RFC822'])[uid][b'RFC822']
                    email_message = email.message_from_bytes(raw_message)
                    
                    # Decode subject
                    subject = ""
                    if email_message['Subject']:
                        decoded_subject = decode_header(email_message['Subject'])
                        subject = "".join([
                            part.decode(encoding or 'utf-8') if isinstance(part, bytes) else part
                            for part, encoding in decoded_subject
                        ])
                    
                    # Only process if it's a reply to our exchange rate alerts
                    if "Exchange Rate Alert" in subject or "Re:" in subject:
                        body = self._extract_email_body(email_message)
                        parsed_adjustments = self._parse_adjustment_commands(body)
                        
                        if parsed_adjustments:
                            adjustments.extend(parsed_adjustments)
                            logger.info(f"Found {len(parsed_adjustments)} adjustment commands in email")
                        
                        # Mark as read
                        server.add_flags([uid], ['\\Seen'])
                        
        except Exception as e:
            logger.error(f"Failed to check inbox: {e}")
            
        return adjustments

    def _extract_email_body(self, email_message) -> str:
        """Extract the body text from an email message."""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    charset = part.get_content_charset() or 'utf-8'
                    body = part.get_payload(decode=True).decode(charset)
                    break
        else:
            charset = email_message.get_content_charset() or 'utf-8'
            body = email_message.get_payload(decode=True).decode(charset)
        
        # Use email reply parser to extract only the reply content
        try:
            reply = EmailReplyParser.parse_reply(body)
            return reply if reply else body
        except:
            return body

    def _parse_adjustment_commands(self, email_body: str) -> List[Dict]:
        """
        Parse adjustment commands from email body.
        
        Expected format examples:
        - ADJUST USD spot_buying_rate max 740
        - ADJUST GBP spot_selling_rate min 920
        - ADJUST JPY spot_selling_rate min 4.80 max 5.20
        - SET USD spot_buying_rate max 735 (replaces existing max)
        - REMOVE USD spot_buying_rate min (removes min condition)
        """
        adjustments = []
        
        # Pattern for ADJUST command
        adjust_pattern = r'ADJUST\s+(\w+)\s+(\w+)\s+((?:min\s+[\d.]+|max\s+[\d.]+|\s+)+)'
        adjust_matches = re.finditer(adjust_pattern, email_body, re.IGNORECASE)
        
        for match in adjust_matches:
            currency_code = match.group(1).upper()
            rate_type = match.group(2).lower()
            conditions_str = match.group(3).strip()
            
            # Parse min/max values
            conditions = {}
            min_match = re.search(r'min\s+([\d.]+)', conditions_str, re.IGNORECASE)
            max_match = re.search(r'max\s+([\d.]+)', conditions_str, re.IGNORECASE)
            
            if min_match:
                conditions['min'] = float(min_match.group(1))
            if max_match:
                conditions['max'] = float(max_match.group(1))
            
            if conditions:
                adjustments.append({
                    'action': 'adjust',
                    'currency_code': currency_code,
                    'rate_type': rate_type,
                    'conditions': conditions
                })
        
        # Pattern for SET command (replaces existing conditions)
        set_pattern = r'SET\s+(\w+)\s+(\w+)\s+((?:min\s+[\d.]+|max\s+[\d.]+|\s+)+)'
        set_matches = re.finditer(set_pattern, email_body, re.IGNORECASE)
        
        for match in set_matches:
            currency_code = match.group(1).upper()
            rate_type = match.group(2).lower()
            conditions_str = match.group(3).strip()
            
            conditions = {}
            min_match = re.search(r'min\s+([\d.]+)', conditions_str, re.IGNORECASE)
            max_match = re.search(r'max\s+([\d.]+)', conditions_str, re.IGNORECASE)
            
            if min_match:
                conditions['min'] = float(min_match.group(1))
            if max_match:
                conditions['max'] = float(max_match.group(1))
            
            if conditions:
                adjustments.append({
                    'action': 'set',
                    'currency_code': currency_code,
                    'rate_type': rate_type,
                    'conditions': conditions
                })
        
        # Pattern for REMOVE command
        remove_pattern = r'REMOVE\s+(\w+)\s+(\w+)\s+(min|max)'
        remove_matches = re.finditer(remove_pattern, email_body, re.IGNORECASE)
        
        for match in remove_matches:
            currency_code = match.group(1).upper()
            rate_type = match.group(2).lower()
            condition_type = match.group(3).lower()
            
            adjustments.append({
                'action': 'remove',
                'currency_code': currency_code,
                'rate_type': rate_type,
                'condition_type': condition_type
            })
        
        return adjustments

    def _apply_adjustments(self, adjustments: List[Dict]) -> bool:
        """Apply setpoint adjustments to the configuration."""
        if not adjustments:
            return False
            
        config_modified = False
        
        for adjustment in adjustments:
            try:
                currency_code = adjustment['currency_code']
                rate_type = adjustment['rate_type']
                action = adjustment['action']
                
                # Find currency by code
                currency_name = None
                currency_index = None
                for i, currency in enumerate(self.config['currencies']):
                    if currency['code'] == currency_code:
                        currency_name = currency['name']
                        currency_index = i
                        break
                
                if currency_index is None:
                    logger.warning(f"Currency code {currency_code} not found in configuration")
                    continue
                
                # Initialize conditions if not exists
                if 'conditions' not in self.config['currencies'][currency_index]:
                    self.config['currencies'][currency_index]['conditions'] = {}
                
                if rate_type not in self.config['currencies'][currency_index]['conditions']:
                    self.config['currencies'][currency_index]['conditions'][rate_type] = {}
                
                if action == 'adjust':
                    # Update existing conditions
                    for condition_type, value in adjustment['conditions'].items():
                        self.config['currencies'][currency_index]['conditions'][rate_type][condition_type] = value
                        logger.info(f"Adjusted {currency_name} {rate_type} {condition_type} to {value}")
                        config_modified = True
                        
                elif action == 'set':
                    # Replace all conditions for this rate type
                    self.config['currencies'][currency_index]['conditions'][rate_type] = adjustment['conditions']
                    logger.info(f"Set {currency_name} {rate_type} conditions to {adjustment['conditions']}")
                    config_modified = True
                    
                elif action == 'remove':
                    # Remove specific condition
                    condition_type = adjustment['condition_type']
                    if condition_type in self.config['currencies'][currency_index]['conditions'][rate_type]:
                        del self.config['currencies'][currency_index]['conditions'][rate_type][condition_type]
                        logger.info(f"Removed {currency_name} {rate_type} {condition_type} condition")
                        config_modified = True
                        
            except Exception as e:
                logger.error(f"Failed to apply adjustment {adjustment}: {e}")
        
        if config_modified:
            self._save_config()
            
        return config_modified

    def _save_config(self):
        """Save the updated configuration back to the YAML file."""
        try:
            with open("config.yaml", "w", encoding="utf-8") as file:
                yaml.dump(self.config, file, default_flow_style=False, allow_unicode=True)
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def _commit_config_changes(self, adjustments: List[Dict]):
        """Commit configuration changes to git repository."""
        try:
            import subprocess
            
            # Configure git user (required for GitHub Actions)
            subprocess.run(["git", "config", "user.name", "Exchange Rate Monitor Bot"], check=True)
            subprocess.run(["git", "config", "user.email", "noreply@github.com"], check=True)
            
            # Check if there are any changes to commit
            result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if not result.stdout.strip():
                logger.info("No configuration changes to commit")
                return
            
            # Add the config file
            subprocess.run(["git", "add", "config.yaml"], check=True)
            
            # Create commit message with adjustment details
            commit_msg = f"Auto-update setpoints - {datetime.now().astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')}\n\nApplied adjustments:\n"
            
            for adjustment in adjustments:
                if adjustment['action'] == 'adjust' or adjustment['action'] == 'set':
                    conditions_str = ", ".join([f"{k}: {v}" for k, v in adjustment['conditions'].items()])
                    commit_msg += f"- {adjustment['action'].title()} {adjustment['currency_code']} {adjustment['rate_type']}: {conditions_str}\n"
                elif adjustment['action'] == 'remove':
                    commit_msg += f"- Remove {adjustment['currency_code']} {adjustment['rate_type']} {adjustment['condition_type']}\n"
            
            # Commit the changes
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            
            # Push the changes (GitHub Actions should handle authentication automatically)
            subprocess.run(["git", "push"], check=True)
            
            logger.info("Configuration changes committed and pushed to repository")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to commit configuration changes: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while committing: {e}")

    def _send_adjustment_confirmation(self, adjustments: List[Dict]):
        """Send confirmation email about applied adjustments."""
        if not adjustments:
            return
            
        subject = f"Setpoint Adjustments Applied - {datetime.now().astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')}"
        
        body = """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2E7D32;">✅ Setpoint Adjustments Applied</h2>
            <p>The following adjustments have been successfully applied to your exchange rate monitoring configuration and committed to the repository:</p>
        """
        
        for adjustment in adjustments:
            if adjustment['action'] == 'adjust' or adjustment['action'] == 'set':
                conditions_str = ", ".join([f"{k}: {v}" for k, v in adjustment['conditions'].items()])
                body += f"""
                <div style="background-color: #E8F5E9; padding: 10px; margin: 10px 0; border-left: 4px solid #2E7D32;">
                    <strong>Action:</strong> {adjustment['action'].title()}<br>
                    <strong>Currency:</strong> {adjustment['currency_code']}<br>
                    <strong>Rate Type:</strong> {adjustment['rate_type']}<br>
                    <strong>Conditions:</strong> {conditions_str}
                </div>
                """
            elif adjustment['action'] == 'remove':
                body += f"""
                <div style="background-color: #FFF3E0; padding: 10px; margin: 10px 0; border-left: 4px solid #FF9800;">
                    <strong>Action:</strong> Remove<br>
                    <strong>Currency:</strong> {adjustment['currency_code']}<br>
                    <strong>Rate Type:</strong> {adjustment['rate_type']}<br>
                    <strong>Removed:</strong> {adjustment['condition_type']} condition
                </div>
                """
        
        body += """
            <hr style="margin: 20px 0;">
            <h3>📝 Email Reply Commands Reference:</h3>
            <div style="background-color: #F5F5F5; padding: 15px; margin: 10px 0;">
                <p><strong>Adjust existing setpoints:</strong></p>
                <code>ADJUST USD spot_buying_rate max 740</code><br>
                <code>ADJUST GBP spot_selling_rate min 920 max 950</code><br><br>
                
                <p><strong>Set new setpoints (replaces existing):</strong></p>
                <code>SET USD spot_buying_rate max 735</code><br><br>
                
                <p><strong>Remove setpoints:</strong></p>
                <code>REMOVE USD spot_buying_rate min</code><br>
                <code>REMOVE JPY spot_selling_rate max</code>
            </div>
            <p><em>Simply reply to any exchange rate alert email with these commands to adjust your monitoring thresholds.</em></p>
        </div>
        """
        
        self._send_email(subject, body)

    def monitor(self):
        """Main monitoring function."""
        logger.info("Starting exchange rate monitoring...")
        
        # First, check inbox for any setpoint adjustments
        logger.info("Checking inbox for setpoint adjustments...")
        adjustments = self._check_inbox_for_adjustments()
        
        if adjustments:
            config_modified = self._apply_adjustments(adjustments)
            if config_modified:
                self._send_adjustment_confirmation(adjustments)
                self._commit_config_changes(adjustments)
                logger.info(f"Applied {len(adjustments)} setpoint adjustments")

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
                f"Exchange Rate Alert - {datetime.now().astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')}"
            )
            # Add reply instructions to the email
            reply_instructions = """
            <hr style="margin: 20px 0;">
            <div style="background-color: #F0F8FF; padding: 15px; margin: 10px 0; border-left: 4px solid #1976D2;">
                <h3 style="color: #1976D2; margin-top: 0;">💡 Quick Setpoint Adjustment</h3>
                <p>Reply to this email with adjustment commands to modify your alert thresholds:</p>
                <div style="font-family: monospace; background-color: #F5F5F5; padding: 10px; margin: 5px 0;">
                    <strong>Examples:</strong><br>
                    ADJUST USD spot_buying_rate max 740<br>
                    ADJUST GBP spot_selling_rate min 920<br>
                    SET JPY spot_selling_rate min 4.80 max 5.20<br>
                    REMOVE USD spot_buying_rate min
                </div>
                <p style="margin-bottom: 0;"><em>Commands are case-insensitive. You can include multiple commands in one reply.</em></p>
            </div>
            """
            body = "\n".join(all_alerts) + reply_instructions
            self._send_email(subject, body)


if __name__ == "__main__":
    monitor = ExchangeRateMonitor()
    monitor.monitor()

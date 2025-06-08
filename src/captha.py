
import requests
import time
from .utils import logger

class Solvium:
    def __init__(self, api_key: str, proxy: str = None):
        self.api_key = api_key
        self.proxy = proxy
        self.base_url = "https://captcha.solvium.io/api/v1"
        self.session = requests.Session()

    def _format_proxy(self, proxy: str) -> str:
        """Format proxy for use in requests."""
        if not proxy:
            return None
        if "@" in proxy:
            return proxy
        return f"http://{proxy}"

    def create_hcaptcha_task(self, sitekey: str, pageurl: str) -> str:
        """Create task for solving hCaptcha."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        }
        url = f"{self.base_url}/task/noname?url={pageurl}&sitekey={sitekey}"
        proxies = {"http": self._format_proxy(self.proxy), "https": self._format_proxy(self.proxy)} if self.proxy else None

        try:
            response = self.session.get(url, headers=headers, proxies=proxies, timeout=30)

            result = response.json()
            if result.get("message") == "Task created" and "task_id" in result:
                return result["task_id"]
            if "Unauthorized" in str(result):
                logger.error("Solvium API key must be specified in config.py")
                return None
            logger.error(f"Error creating hCaptcha task: {result}")
            return None
        except Exception as e:
            logger.error(f"Error creating hCaptcha task: {e}")
            return None

    def create_turnstile_task(self, challenge_token: str) -> str:
        """Create task for solving Cloudflare Turnstile."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        }
        proxies = {"http": self._format_proxy(self.proxy), "https": self._format_proxy(self.proxy)} if self.proxy else None
        url = f"{self.base_url}/task/vercel/"

        try:
            response = self.session.get(
                url,
                params={"challengeToken": challenge_token},
                headers=headers,
                proxies=proxies,
                timeout=30
            )

            result = response.json()
            if "task_id" in result:
                return result["task_id"]
            if "Unauthorized" in str(result):
                logger.error("Solvium API key must be specified in config.py")
                return None
            logger.error(f"Error creating Turnstile task: {result}")
            return None
        except Exception as e:
            logger.error(f"Error creating Turnstile task: {e}")
            return None

    def create_recaptcha_v3_task(self, sitekey: str, pageurl: str, action: str, enterprise: bool = False) -> str:
        """Create task for solving reCAPTCHA v3."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        }
        proxies = {"http": self._format_proxy(self.proxy), "https": self._format_proxy(self.proxy)} if self.proxy else None
        url = f"{self.base_url}/task/"
        params = {
            "url": pageurl,
            "sitekey": sitekey,
            "action": action,
        }
        if enterprise:
            params["enterprise"] = "true"

        try:
            response = self.session.get(
                url,
                headers=headers,
                params=params,
                proxies=proxies,
                timeout=30
            )
            
            result = response.json()
            if result.get("message") == "Task created" and "task_id" in result:
                return result["task_id"]
            if "Unauthorized" in str(result):
                logger.error("Solvium API key must be specified in config.py")
                return None
            logger.error(f"Error creating reCAPTCHA v3 task: {result}")
            return None
        except Exception as e:
            logger.error(f"Error creating reCAPTCHA v3 task: {e}")
            return None

    def create_cf_clearance_task(self, pageurl: str, body_b64: str, proxy: str) -> str:
        """Create task for solving Cloudflare challenge."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }    
        json_data = {
            "url": pageurl,
            "body": body_b64,
            "proxy": proxy if proxy else None,
        }
        url = f"{self.base_url}/task/cf-clearance"

        try:
            response = self.session.post(
                url,
                headers=headers,
                json=json_data,
                timeout=30
            )
            
            result = response.json()
            if result.get("message") == "Task created" and "task_id" in result:
                return result["task_id"]
            if "Unauthorized" in str(result):
                logger.error("Solvium API key must be specified in config.py")
                return None
            logger.error(f"Error creating CF clearance task: {result}")
            return None
        except Exception as e:
            logger.error(f"Error creating CF clearance task: {e}")
            return None

    def get_task_result(self, task_id: str) -> str:
        """Retrieve captcha solution result."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        max_attempts = 30

        for _ in range(max_attempts):
            try:
                response = self.session.get(
                    f"{self.base_url}/task/status/{task_id}",
                    headers=headers,
                    timeout=30
                )
                result = response.json()
                if result.get("status") == "completed" and result.get("result") and result["result"].get("solution"):
                    return result["result"]["solution"]
                elif result.get("status") in ["running", "pending"]:
                    time.sleep(5)
                    continue
                else:
                    logger.error(f"Error retrieving result: {result}")
                    return None
            except Exception as e:
                logger.error(f"Error retrieving result: {e}")
                return None

        logger.error("Maximum attempts reached without result")
        return None

    def solve_captcha(self, sitekey: str, pageurl: str) -> str:
        """Solve hCaptcha."""
        task_id = self.create_hcaptcha_task(sitekey, pageurl)
        if not task_id:
            return None
        return self.get_task_result(task_id)

    def solve_turnstile(self, challenge_token: str) -> str:
        """Solve Cloudflare Turnstile captcha."""
        task_id = self.create_turnstile_task(challenge_token)
        if not task_id:
            return None
        return self.get_task_result(task_id)

    def solve_recaptcha_v3(self, sitekey: str, pageurl: str, action: str, enterprise: bool = False) -> str:
        """Solve reCAPTCHA v3."""
        task_id = self.create_recaptcha_v3_task(sitekey, pageurl, action, enterprise)
        if not task_id:
            return None
        return self.get_task_result(task_id)

    def solve_cf_clearance(self, pageurl: str, body_b64: str, proxy: str) -> str:
        """Solve Cloudflare challenge and return cf_clearance."""
        task_id = self.create_cf_clearance_task(pageurl, body_b64, proxy)
        if not task_id:
            return None
        return self.get_task_result(task_id)





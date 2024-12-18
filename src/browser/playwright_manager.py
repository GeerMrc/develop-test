from playwright.sync_api import sync_playwright
from ..utils.logger import Logger

class PlaywrightManager:
    def __init__(self):
        self.logger = Logger(__name__)
        self.browser = None
        self.context = None
        self.page = None
        
    def start_browser(self, headless=False):
        """启动浏览器"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=headless)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
            self.logger.info("浏览器启动成功")
            return self.page
        except Exception as e:
            self.logger.error(f"浏览器启动失败: {str(e)}")
            raise
            
    def close(self):
        """关闭浏览器"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.logger.info("浏览器已关闭")
        except Exception as e:
            self.logger.error(f"关闭浏览��时出错: {str(e)}") 
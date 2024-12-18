import asyncio
from datetime import datetime
import os
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

class BrowserManager:
    """浏览器管理类"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self._playwright = None
        self._browser = None
        self._context = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self._playwright = await async_playwright().start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
            
    async def get_browser(self, browser_type='chrome', show=False) -> tuple[Browser, BrowserContext, Page]:
        """获取配置的浏览器实例"""
        if not self._playwright:
            self._playwright = await async_playwright().start()
            
        # 获取浏览器配置
        browser_config = self.config.get(f'browsers.{browser_type}')
        if not browser_config:
            raise ValueError(f"未找到浏览器配置: {browser_type}")
            
        # 获取浏览器实例
        browser_launcher = getattr(self._playwright, browser_config.get('name', browser_type))
        self._browser = await browser_launcher.launch(
            headless=not show,
            args=browser_config.get('launch_args', [])
        )
        
        # 创建上下文
        self._context = await self.setup_context(self._browser, browser_config)
        
        # 创建新页面
        page = await self._context.new_page()
        
        return self._browser, self._context, page
            
    async def setup_context(self, browser, browser_config):
        """
        设置浏览器上下文
        
        Args:
            browser: 浏览器实例
            browser_config: 浏览器配置
            
        Returns:
            BrowserContext: 浏览器上下文
        """
        context = await browser.new_context(
            viewport=browser_config.get('viewport'),
            user_agent=browser_config.get('user_agent'),
            ignore_https_errors=browser_config.get('options', {}).get('ignore_https_errors', True)
        )
        
        # 设置额外的 headers
        headers = browser_config.get('headers', {})
        if headers:
            await context.set_extra_http_headers(headers)
            
        return context
        
    async def load_page(self, page, url, wait_selectors=None):
        """
        加载页面等待指定元素
        
        Args:
            page: 页面对象
            url: 要加载的URL
            wait_selectors: 需要等待的选择器列表
            
        Returns:
            str: 页面内容
        """
        try:
            self.logger.info("正在加载页面...")
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            self.logger.info("页面加载完成")
            
            # 等待页面稳定
            await page.wait_for_load_state('networkidle', timeout=30000)
            self.logger.info("页面网络请求已稳定")
            
            # 等待指定元素
            if wait_selectors:
                for selector in wait_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        self.logger.info(f"找到页面元素: {selector}")
                        break
                    except:
                        continue
            
            # 等待一下以确保动态内容加载完成
            await asyncio.sleep(2)
            
            return await page.content()
            
        except Exception as e:
            self.logger.error(f"加载页面失败: {str(e)}")
            raise
            
    async def save_screenshot(self, page, config, browser_type, product_id=None):
        """
        保存页面截图
        
        Args:
            page: 页面对象
            config: 配置对象
            browser_type: 浏览器类型
            product_id: 商品ID
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = os.path.join(
            config.get('paths.images'),
            f"screenshot_{product_id}_{browser_type}_{timestamp}.png"
        )
        await page.screenshot(path=screenshot_path, full_page=True)
        self.logger.info(f"页面截图已保存: {screenshot_path}") 
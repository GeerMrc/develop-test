from ..browser.playwright_manager import PlaywrightManager
from ..utils.logger import Logger
from ..utils.config import Config
from ..exceptions.custom_exceptions import LoginError
from PIL import Image
import io
import time
import requests
from requests.cookies import RequestsCookieJar

class LoginManager:
    def __init__(self):
        self.logger = Logger(__name__)
        self.config = Config()
        self.browser_manager = PlaywrightManager()
        self.session = requests.session()
        self._setup_session()

    def _setup_session(self):
        """设置session的headers等信息"""
        self.session.headers.update({
            'User-Agent': self.config.get('browser.user_agent')
        })

    async def login(self):
        """执行登录流程"""
        try:
            self.logger.info("开始登录流程")
            page = await self._init_page()
            
            # 访问登录页并等待加载完成
            await self._goto_login_page(page)
            
            # 切换到扫码登录并获取二维码
            await self._switch_to_qrcode(page)
            
            # 等待扫码登录
            await self._wait_for_login(page)
            
            # 获取cookies并更新session
            await self._update_cookies(page)
            
            # 验证登录状态
            if self.check_login_status():
                self.logger.info("登录成功并验证!")
                return True
            else:
                raise LoginError("登录状态验证失败")

        except Exception as e:
            self.logger.error(f"登录失败: {str(e)}")
            raise LoginError(f"登录过程出错: {str(e)}")
        finally:
            await self.browser_manager.close()

    async def _init_page(self):
        """初始化浏览器页面"""
        page = await self.browser_manager.start_browser(
            headless=self.config.get('browser.headless', False)
        )
        # 设置视窗大小
        viewport = self.config.get('browser.viewport', {})
        await page.set_viewport_size({
            'width': viewport.get('width', 1280),
            'height': viewport.get('height', 800)
        })
        return page

    async def _goto_login_page(self, page):
        """访问登录页"""
        login_url = self.config.get('urls.login')
        self.logger.debug(f"访问登录页: {login_url}")
        await page.goto(login_url)
        # 等待页面加载完成
        await page.wait_for_load_state('networkidle')

    async def _switch_to_qrcode(self, page):
        """切换到扫码登录模式"""
        try:
            qrcode_tab = self.config.get('selectors.login.qrcode_tab')
            await page.click(qrcode_tab)
            await page.wait_for_timeout(
                self.config.get('timeouts.qrcode_wait')
            )
            await self._handle_qrcode(page)
        except Exception as e:
            self.logger.error("切换到扫码登录失败")
            raise LoginError(f"切换扫码登录失败: {str(e)}")

    async def _handle_qrcode(self, page):
        """处理二维码获取和显示"""
        try:
            qr_selector = self.config.get('selectors.login.qrcode')
            qr_element = page.locator(qr_selector)
            qr_screenshot = await qr_element.screenshot()
            
            # 保存并显示二维码
            qr_image = Image.open(io.BytesIO(qr_screenshot))
            qr_image.save('qrcode.png')
            qr_image.show()
            
            self.logger.info("二维码已生成,请扫码登录")
        except Exception as e:
            self.logger.error(f"获取二维码失败: {str(e)}")
            raise LoginError("二维码获取失败")

    async def _wait_for_login(self, page):
        """等待用户扫码登录"""
        try:
            username_selector = self.config.get('selectors.login.username')
            timeout = self.config.get('timeouts.login')
            
            # 等待用户名元素出现,表示登录成功
            await page.wait_for_selector(
                username_selector, 
                timeout=timeout,
                state='visible'
            )
            username = await page.locator(username_selector).text_content()
            self.logger.info(f"检测到登录用户: {username}")
            
        except Exception as e:
            self.logger.error("登录超时或失败")
            raise LoginError("等待登录超时")

    async def _update_cookies(self, page):
        """更新session的cookies"""
        try:
            cookies = await self.browser_manager.context.cookies()
            tmp_cookies = RequestsCookieJar()
            
            for cookie in cookies:
                tmp_cookies.set(cookie["name"], cookie["value"])
            
            self.session.cookies.update(tmp_cookies)
            self.logger.debug("Cookies已更新")
            
        except Exception as e:
            self.logger.error(f"更新Cookies失败: {str(e)}")
            raise LoginError("Cookies更新失败")

    def check_login_status(self):
        """检查登录状态"""
        try:
            check_url = self.config.get('urls.check_login')
            response = self.session.get(check_url)
            success_key = self.config.get('selectors.login.login_success_key')
            return success_key in response.text
        except Exception as e:
            self.logger.error(f"检查登录状态失败: {str(e)}")
            return False 
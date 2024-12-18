import pytest
import os
from src.utils.config import Config
from src.utils.logger import setup_logger
from src.utils.browser import BrowserManager

@pytest.fixture
def config():
    """配置对象夹具"""
    if not os.environ.get('CONFIG_PATH'):
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
        os.environ['CONFIG_PATH'] = config_path
    return Config()

@pytest.fixture
def logger():
    """日志对象夹具"""
    return setup_logger('test_browser')

@pytest.fixture
async def browser_manager(config, logger):
    """浏览器管理器夹具"""
    async with BrowserManager(config, logger) as manager:
        yield manager

@pytest.mark.asyncio
async def test_browser_launch(browser_manager):
    """测试浏览器启动"""
    browser, context, page = await browser_manager.get_browser('chrome')
    assert browser is not None
    assert context is not None
    assert page is not None

@pytest.mark.asyncio
async def test_page_load(browser_manager):
    """测试页面加载"""
    browser, context, page = await browser_manager.get_browser('chrome')
    # 加载测试页面
    test_url = "https://www.baidu.com"
    content = await browser_manager.load_page(page, test_url)
    assert content is not None
    assert "百度" in content

@pytest.mark.asyncio
async def test_screenshot(browser_manager, config):
    """测试截图功能"""
    browser, context, page = await browser_manager.get_browser('chrome')
    # 加载页面并截图
    test_url = "https://www.baidu.com"
    await browser_manager.load_page(page, test_url)
    await browser_manager.save_screenshot(page, config, 'chrome', 'test')
    
    # 验证截图文件是否存在
    screenshots = os.listdir(config.get('paths.images'))
    assert any(s.startswith('screenshot_test_chrome_') for s in screenshots)

@pytest.mark.asyncio
@pytest.mark.parametrize('browser_type', ['chrome', 'firefox', 'webkit'])
async def test_multiple_browsers(browser_manager, browser_type):
    """测试多浏览器支持"""
    browser, context, page = await browser_manager.get_browser(browser_type)
    assert browser is not None
    assert context is not None
    assert page is not None

@pytest.mark.asyncio
async def test_browser_options(browser_manager):
    """测试浏览器选项设置"""
    browser, context, page = await browser_manager.get_browser('chrome', show=True)
    
    # ��证浏览器选项
    browser_config = browser_manager.config.get('browsers.chrome')
    expected_viewport = browser_config.get('viewport')
    actual_viewport = page.viewport_size
    
    # 验证视口大小
    assert actual_viewport['width'] == expected_viewport['width'], \
        f"视口宽度不匹配: 期望 {expected_viewport['width']}, 实际 {actual_viewport['width']}"
    assert actual_viewport['height'] == expected_viewport['height'], \
        f"视口高度不匹配: 期望 {expected_viewport['height']}, 实际 {actual_viewport['height']}"
    
    # 验证其他浏览器选项
    # 获取实际的 User Agent
    actual_user_agent = await page.evaluate('navigator.userAgent')
    expected_user_agent = browser_config.get('user_agent')
    
    assert actual_user_agent == expected_user_agent, \
        f"User Agent 不匹配:\n期望: {expected_user_agent}\n实际: {actual_user_agent}"
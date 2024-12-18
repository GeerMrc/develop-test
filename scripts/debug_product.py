import sys
import os
import asyncio
import json
from datetime import datetime
import argparse
from playwright.async_api import async_playwright
from src.core.product import ProductManager
from src.utils.config import Config
from src.utils.logger import setup_logger
from src.utils.browser import BrowserManager
from src.utils.result_formatter import ResultFormatter

# 设置配置文件路径
if not os.environ.get('CONFIG_PATH'):
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
    os.environ['CONFIG_PATH'] = config_path

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Tmall Taobao Product Information Scraper Tool',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''
  -b, --browser                                            Specify browser type to use {chrome,firefox,webkit} (default: all)
  --show                                                   Show browser UI (default: headless mode)

Browser Types:
  chrome                                                   Chrome/Chromium browser
  firefox                                                  Firefox browser
  webkit                                                   Safari/WebKit browser
  all                                                      All supported browsers (default)
'''
    )
    parser.add_argument('-b', '--browser',
                       choices=['chrome', 'firefox', 'webkit', 'all'],
                       default='all',
                       metavar='',
                       help=argparse.SUPPRESS)
    parser.add_argument('--show',
                       action='store_true',
                       help=argparse.SUPPRESS)
    return parser.parse_args()

async def debug_product_info(browser_type='chrome', show=False):
    """调试商品信息获取"""
    config = Config()
    logger = setup_logger(f'debug_{browser_type}')
    browser_manager = BrowserManager(config, logger)
    
    # 记录运行模式
    mode = "有界面" if show else "无界面"
    logger.info(f"运行模式: {mode}")
    
    # 确保所有必要的目录存在
    for path_key in ['logs', 'images', 'results', 'debug']:
        path = config.get(f'paths.{path_key}')
        if path:
            os.makedirs(path, exist_ok=True)
    
    try:
        # 1. 测试时间同步
        logger.info("=" * 50)
        logger.info(f"使用浏览器: {browser_type}")
        logger.info("开始测试时间同步...")
        logger.info("=" * 50)
        
        product_manager = ProductManager(None)  # 不使用 requests session
        server_time = product_manager.time_sync.get_server_time('taobao')
        local_time = datetime.now()
        offset = product_manager.time_sync.get_time_offset('taobao')
        
        logger.info(f"服务器时间: {server_time}")
        logger.info(f"本地时间: {local_time}")
        logger.info(f"时间偏移: {offset:.3f}秒")
        
        # 2. 测试商品信息获取
        logger.info("\n" + "=" * 50)
        logger.info("开始测试商品信息获取...")
        logger.info("=" * 50)
        
        product_config = config.get('urls.product.maotai')
        # 组合完整的商品URL
        base_url = product_config['url']
        url = f"{base_url}&skuId={product_config['skuId']}"
        
        logger.info(f"商品URL: {url}")
        logger.info(f"商品ID: {product_config['id']}")
        
        # 使用新的浏览器管理器
        browser, context, page = await browser_manager.get_browser(browser_type, show)
        try:
            wait_selectors = [
                'div.tb-detail-hd',
                'h1.tb-main-title',
                'div.ItemHeader--root--zK3Zc9m'
            ]
            html_content = await browser_manager.load_page(page, url, wait_selectors)
            await browser_manager.save_screenshot(page, config, browser_type, product_config['id'])
        finally:
            await context.close()
            await browser.close()
        
        # 保存页面内容
        debug_dir = config.get('paths.debug')
        page_file = os.path.join(debug_dir, f"page_{product_config['id']}_{browser_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        with open(page_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"页面内容已保存: {page_file}")
        
        # 解析商品信息
        product_info = await product_manager.parse_product_info(html_content, url)
        
        # 保存调试结果
        debug_file = os.path.join(
            config.get('paths.results'),
            f"product_info_{product_config['id']}_{browser_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        # 格式化结果
        formatted_result = ResultFormatter.format_test_result(
            browser_type=browser_type,
            browser_info={
                'type': browser_type,
                'headless': not show,
                'user_agent': config.get(f'browsers.{browser_type}.user_agent'),
                'viewport': config.get(f'browsers.{browser_type}.viewport')
            },
            product_info=product_info,
            server_time=server_time,
            time_offset=offset,
            url=url,
            performance_metrics={
                'page_load_time': None,  # TODO: 添加页面加载时间
                'parse_time': None,      # TODO: 添加解析时间
                'total_time': None       # TODO: 添加总耗时
            }
        )
        
        # 保存格式化后的结果
        ResultFormatter.save_result(formatted_result, debug_file)
        
        logger.info(f"\n调试结果已保存: {debug_file}")
        
        # 3. 验证关键信息
        if product_info:
            logger.info("\n" + "=" * 50)
            logger.info("商品信息验证:")
            logger.info("=" * 50)
            logger.info(f"- 标题: {product_info.get('title')}")
            logger.info(f"- 价格: {product_info.get('price_info')}")
            logger.info(f"- 抢购时间: {product_info.get('target_time')}")
            logger.info(f"- 图片数量: {len(product_info.get('images', []))}")
            
            # 显示图片保存结果
            images = product_info.get('images', [])
            if images:
                logger.info("\n图片保存结果:")
                for img in images:
                    status = "✓" if img['status'] == 'success' else "✗"
                    if img['status'] == 'success':
                        size_kb = img['file_size'] / 1024
                        logger.info(f"{status} {img['saved_path']} ({size_kb:.1f}KB)")
                    else:
                        logger.info(f"{status} {img['original_url']} - {img.get('error', '未知错误')}")
        else:
            logger.error("未获取到商品信息")
            
    except Exception as e:
        logger.error(f"调试过程出错: {str(e)}", exc_info=True)

async def main():
    """主函数"""
    args = parse_args()
    if args.browser == 'all':
        # 测试所有浏览器
        browsers = ['chrome', 'firefox', 'webkit']
        for browser in browsers:
            try:
                await debug_product_info(browser, args.show)
            except Exception as e:
                print(f"{browser} 测试失败: {str(e)}")
    else:
        # 测试指定浏览器
        await debug_product_info(args.browser, args.show)

if __name__ == "__main__":
    asyncio.run(main()) 
from ..utils.logger import setup_logger
from ..utils.config import Config
from ..exceptions.custom_exceptions import ProductError
import re
import time
import asyncio
import random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ..utils.time_sync import TimeSync
from ..utils.image_handler import ImageHandler
from lxml import etree
import json
import os
import aiohttp
from typing import Optional, List, Dict, Any

class ProductManager:
    def __init__(self, session):
        """初始化商品管理器"""
        self.session = session
        self.config = Config()
        self.logger = setup_logger('product')
        self.time_sync = TimeSync()
        self.product_info = None
        self.update_task = None
        self.is_running = False
        self.time_offset = 0
        
        # 从配置文件加载重试参数
        self.retry_count = self.config.get('monitoring.retry.count', 3)
        self.retry_interval = self.config.get('monitoring.retry.interval', 5)
        
        self.image_handler = ImageHandler()
        
        self.last_countdown_log = 0  # 用于控制倒计时��频率
        
    async def start_monitoring(self, url):
        """开始监控商品信息"""
        # 获取时偏移
        self.time_offset = self.time_sync.get_time_offset('taobao')
        self.logger.info(f"系统时间偏移: {self.time_offset:.3f} 秒")
        
        self.is_running = True
        self.url = url
        
        # 首次获取商品信息
        self.product_info = await self.get_product_info(url)
        
        # 启动后台更新任务
        self.update_task = asyncio.create_task(self._periodic_update())
        
        return self.product_info

    async def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        self.logger.info("商品监控停止")

    async def _periodic_update(self):
        """优化定期更新逻辑"""
        try:
            while self.is_running:
                current_time = datetime.now()
                target_time = datetime.fromtimestamp(self.product_info['timestamp'])
                time_diff = (target_time - current_time).total_seconds()

                # 显示倒计时
                if self._should_log_countdown(time_diff):
                    countdown_msg = self._format_countdown(time_diff)
                    self.logger.info(countdown_msg)

                # 根据距离目标时间的远近调整更新频率
                if time_diff < 3600:  # 距离抢购时间不到1小时
                    if time_diff <= 600:  # 最后10分钟
                        wait_seconds = 0.1  # 每0.1秒更新一次
                    else:
                        wait_minutes = random.uniform(1, 3)  # 更频繁检查
                        wait_seconds = wait_minutes * 60
                    self.logger.info("抢购时间临近，提高更新频率")
                else:
                    wait_minutes = random.uniform(45, 75)
                    wait_seconds = wait_minutes * 60
                    self.logger.debug(f"下次更新将在 {wait_minutes:.2f} 分钟后进行")

                # 更新时间偏移和商品信息
                self.time_offset = self.time_sync.get_time_offset('taobao', force_sync=(time_diff < 600))
                if time_diff > 10:  # 距离抢购还有超过10秒时才更新商品信息
                    await self._update_product_info()
                
                await asyncio.sleep(wait_seconds)

        except Exception as e:
            self.logger.error(f"新任务异常: {str(e)}")
            raise

    async def _update_product_info(self):
        """添加重试机制的商品信息更新"""
        for attempt in range(self.retry_count):
            try:
                new_info = await self.get_product_info(self.url)
                
                if self._validate_product_info(new_info):
                    if self._check_info_changes(new_info):
                        self._log_changes(self.product_info, new_info)
                        # 如果抢购时间变化，可能需要调整策略
                        if new_info['target_time'] != self.product_info['target_time']:
                            self.logger.warning("抢购时间发生变化，请注意调整抢购策略")
                    
                    self.product_info = new_info
                    self.last_check_time = datetime.now()
                    return True
                    
            except Exception as e:
                if attempt == self.retry_count - 1:
                    self.logger.error(f"更新商品信息失败，已重试{self.retry_count}次")
                    raise
                self.logger.warning(f"第{attempt + 1}次更新失败，准备重试")
                await asyncio.sleep(self.retry_interval)

    def _validate_product_info(self, info):
        """验证���品信息的完整性和有效性"""
        required_fields = ['title', 'price_info', 'target_time', 'timestamp']
        
        if not all(field in info for field in required_fields):
            self.logger.error("商品信息不完整")
            return False
            
        if not info['target_time'] or not info['timestamp']:
            self.logger.error("抢购时间信息无效")
            return False
            
        return True

    def _check_info_changes(self, new_info):
        """检查商品信息是否发生变化"""
        if not self.product_info:
            return True
            
        # 检查关键信息是否变化
        changes = (
            new_info['title'] != self.product_info['title'] or
            new_info['price_info'] != self.product_info['price_info'] or
            new_info['target_time'] != self.product_info['target_time']
        )
        return changes

    def _log_changes(self, old_info, new_info):
        """记录变化的信息"""
        if old_info['title'] != new_info['title']:
            self.logger.info(f"商品标题变化: {old_info['title']} -> {new_info['title']}")
            
        if old_info['price_info'] != new_info['price_info']:
            self.logger.info(f"价格信息变化: {old_info['price_info']} -> {new_info['price_info']}")
            
        if old_info['target_time'] != new_info['target_time']:
            self.logger.info(f"抢购时间变化: {old_info['target_time']} -> {new_info['target_time']}")

    def _extract_images(self, html_content):
        """提取商品图片"""
        try:
            tree = etree.HTML(html_content)
            images = []
            
            # 使用 XPath 获取所有 thumbnailPic--QasTmWDm class 的图片
            img_elements = tree.xpath("//img[@class='thumbnailPic--QasTmWDm']")
            if not img_elements:
                # 如果没到，尝试模糊匹配
                img_elements = tree.xpath("//img[contains(@class, 'thumbnailPic--QasTmWDm')]")
            
            server_time = self.time_sync.get_server_time('taobao')
            self.logger.info(f"开始提取商品图片 [服务器时间: {server_time.strftime('%Y-%m-%d %H:%M:%S')}]")
            self.logger.info(f"找到 {len(img_elements)} 张商品图片")
            
            # 遍历所有找到的图片元素
            for index, img in enumerate(img_elements, 1):
                src = img.get('src')
                placeholder = img.get('placeholder', '')
                
                self.logger.debug(f"处理第 {index} 张图片:")
                self.logger.debug(f"- 原�� src: {src}")
                self.logger.debug(f"- placeholder: {placeholder}")
                
                if src:
                    # 处理相对路径
                    if src.startswith('//'):
                        src = 'https:' + src
                    
                    # 获取原图（移除各种后缀）
                    src = re.sub(r'_q\d+\.jpg|_\d+x\d+\.(jpg|png|webp)|_.webp', '', src)
                    src = re.sub(r'\?(.*)', '', src)  # 移除URL参数
                    
                    # 确保URL以图片扩展名结尾
                    if not src.endswith(('.jpg', '.png', '.webp')):
                        src += '.jpg'
                    
                    image_info = {
                        'url': src,
                        'type': 'product',
                        'index': index,
                        'extract_time': server_time.isoformat()
                    }
                    images.append(image_info)
                    self.logger.debug(f"✓ 成功提取图片 {index}: {src}")
                else:
                    self.logger.warning(f"✗ 图片 {index} 没有有效的src属性")
            
            if not images:
                self.logger.warning("未找到任何商品图片")
                return None
            
            self.logger.info(f"成功提取 {len(images)} 张商品图片")
            return images
            
        except Exception as e:
            self.logger.error(f"提取商品图片失败: {str(e)}")
            return None

    async def get_product_info(self, url: str) -> dict:
        """获取商品信息"""
        try:
            self.logger.info("开始获取商品信息")
            
            # 从配置中获取商品信息
            product_config = self.config.get('urls.product.maotai')
            if not product_config:
                raise ValueError("未找到商品配置")
            
            # 获取商品ID和完整URL
            product_id = product_config['id']
            if 'skuId' not in url:
                url = f"{url}&skuId={product_config['skuId']}"
            self.logger.debug(f"完整商品URL: {url}")
            
            # 获取页面内容
            response = self.session.get(url)
            if response.status_code != 200:
                raise ValueError(f"获取页面失败: {response.status_code}")
            
            return await self.parse_product_info(response.text, url)
            
        except Exception as e:
            self.logger.error(f"获取商品信息失败: {str(e)}")
            raise ProductError(f"获取商品信息失败: {str(e)}")

    async def parse_product_info(self, html_content: str, url: str) -> dict:
        """解析商品信息"""
        try:
            # 从配置中获取商品信息
            product_config = self.config.get('urls.product.maotai')
            if not product_config:
                raise ValueError("未找到商品配置")
            
            product_id = product_config['id']
            
            # 提取图片
            images = self._extract_images(html_content)
            
            # 使用 asyncio.gather 等待所有图片保存完成
            if images:
                tasks = []
                for img in images:
                    task = asyncio.create_task(self._save_single_image(img, product_id))
                    tasks.append(task)
                saved_images = await asyncio.gather(*tasks)
            else:
                saved_images = []
            
            # 获取所有商品信息
            product_info = {
                'product_id': product_id,
                'title': self._extract_title(html_content),
                'price_info': self._extract_price_info(html_content),
                'target_time': self._extract_target_time(html_content),
                'images': saved_images
            }
            
            # 如果没有获取到抢购时间，使用配置文件的默认时间
            if not product_info['target_time']:
                self.logger.warning("未从页面获取到抢购时间，将使用配置文件中的默认时间")
                product_info['target_time'] = self.config.get('order.target_time')
            
            # 添加时间戳
            product_info['timestamp'] = self._convert_to_timestamp(product_info['target_time'])
            
            self.logger.info("商品信息获取成功:")
            self.logger.info(f"商品名称: {product_info['title']}")
            self.logger.info(f"价格信息: {product_info['price_info']}")
            self.logger.info(f"抢购时间: {product_info['target_time']}")
            
            return product_info
            
        except Exception as e:
            self.logger.error(f"解析商品信息失败: {str(e)}")
            raise ProductError(f"解析商品信息失败: {str(e)}")

    def _extract_title(self, html_content):
        """提取商品标题"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 尝试多个可能的选择器
            title_selectors = [
                'h1.tb-main-title',
                'h1.tb-detail-hd',
                'div.tb-detail-hd h1',
                'h1[class*="title"]',
                'h1[class*="Title"]'
            ]
            
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element:
                    break

            if title_element:
                title = title_element.text.strip()
                self.logger.debug(f"提取到商品标题: {title}")
                return title
            
            # 如果上述选择器都失败，尝试使用 XPath
            tree = etree.HTML(html_content)
            xpath_selectors = [
                "//h1[contains(@class, 'mainTitle')]",
                "//div[contains(@class, 'ItemHeader')]//h1",
                "//div[@class='tb-detail-hd']//h1",
                "//div[contains(@class, 'Title')]//h1"
            ]
            
            for xpath in xpath_selectors:
                elements = tree.xpath(xpath)
                if elements:
                    title = elements[0].text.strip()
                    self.logger.debug(f"通过XPath提取到标题: {title}")
                    return title
            
            self.logger.warning("未找到商品标题")
            return None
            
        except Exception as e:
            self.logger.error(f"提取商品标题失败: {str(e)}")
            return None

    def _extract_price_info(self, html_content):
        """提取价格信息"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            price_info = {
                'promotion': None,
                'price': None,
                'sales': None
            }
            
            # 尝试多个可能的价格选择器
            price_selectors = [
                'div[class*="PriceModule"] span[class*="price"]',
                'div[class*="Price"] span[class*="price"]',
                'div[class*="priceWrap"] span[class*="text"]'
            ]
            
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    try:
                        price_text = price_element.text.strip().replace('¥', '').replace(',', '')
                        price_info['price'] = float(price_text)
                        break
                    except ValueError:
                        self.logger.warning(f"无法转换价格: {price_element.text}")
            
            # 尝试提取促销信息
            promo_selectors = [
                'div[class*="Promotion"] span',
                'div[class*="promotion"] span',
                'span[class*="title"]'
            ]
            
            for selector in promo_selectors:
                promo_element = soup.select_one(selector)
                if promo_element:
                    price_info['promotion'] = promo_element.text.strip()
                    break
            
            # 尝试提取销量信息
            sales_selectors = [
                'div[class*="Sales"]',
                'div[class*="sales"]',
                'div[class*="salesDesc"]'
            ]
            
            for selector in sales_selectors:
                sales_element = soup.select_one(selector)
                if sales_element:
                    price_info['sales'] = sales_element.text.strip()
                    break
            
            if any(price_info.values()):
                self.logger.debug(f"提取到价格信息: {price_info}")
                return price_info
            
            self.logger.warning("未找到价格信息")
            return None
            
        except Exception as e:
            self.logger.error(f"提取价格信息失败: {str(e)}")
            return None

    def _extract_target_time(self, html_content):
        """从页面内中提取抢购时间"""
        try:
            time_pattern = self.config.get('selectors.product.time.pattern')
            if not isinstance(time_pattern, str):
                self.logger.error(f"无效的时间模式: {time_pattern}")
                return None
            
            match = re.search(time_pattern, html_content)
            
            if match:
                date_str, time_str = match.groups()
                return self._parse_time_string(f"{date_str} {time_str}")
            
            # 如果没有找到时间，使用配置文件中的默认时间
            default_time = self.config.get('order.target_time')
            if default_time:
                self.logger.warning("未从页面获取到抢购时间，使用配置文件中的默认时间")
                return default_time
            
            self.logger.error("无法获取抢购时间")
            return None
            
        except Exception as e:
            self.logger.error(f"提取抢购时间失败: {str(e)}")
            return None

    def _parse_time_string(self, time_str):
        """
        解析时间字符串为标准格式
        输入格式: "12.18 20:00"
        输出格式: "YYYY/MM/DD HH:MM:SS"
        """
        try:
            # 分解日期和时间
            date_part, time_part = time_str.split()
            month, day = date_part.split('.')
            hour, minute = time_part.split(':')
            
            # 获取当前年份
            current_year = datetime.now().year
            
            # 构建完整的时间字符串
            formatted_time = f"{current_year}/{month}/{day} {hour}:{minute}:00"
            
            # 验证时间格式
            datetime.strptime(formatted_time, "%Y/%m/%d %H:%M:%S")
            
            self.logger.debug(f"解析得到的时间: {formatted_time}")
            return formatted_time
            
        except Exception as e:
            self.logger.error(f"解析时间字符串失败: {str(e)}")
            return None

    def _convert_to_timestamp(self, time_str):
        """将间字符串转换为时间戳（考虑服务器时间偏移）"""
        try:
            if not time_str:
                raise ValueError("时间字符串不能为空")
            
            time_array = time.strptime(time_str, "%Y/%m/%d %H:%M:%S")
            timestamp = time.mktime(time_array)
            
            # 获取当前服务器时间
            server_time = self.time_sync.get_server_time('taobao')
            if server_time:
                current_timestamp = server_time.timestamp()
            else:
                current_timestamp = time.time() + self.time_offset
            
            # 检查时间戳是否有效
            if timestamp < current_timestamp:
                self.logger.warning("检测到过期的抢购时间，可能需要更新")
            
            return timestamp
            
        except Exception as e:
            self.logger.error(f"转换时间戳失败: {str(e)}")
            raise ProductError("时间格式转换失败") 

    def _format_countdown(self, seconds_left):
        """格式化倒计时显示"""
        if seconds_left <= 0:
            return "抢购已开始"
        
        if seconds_left > 600:  # 大于10分
            hours = int(seconds_left // 3600)
            minutes = int((seconds_left % 3600) // 60)
            seconds = int(seconds_left % 60)
            if hours > 0:
                return f"距离抢购还有: {hours}小时{minutes}分钟{seconds:02d}秒"
            else:
                return f"距离抢购还有: {minutes}分钟{seconds:02d}秒"
        elif seconds_left > 60:  # 1-10分钟
            minutes = int(seconds_left // 60)
            seconds = seconds_left % 60
            return f"距离抢购还有: {minutes}分钟{seconds:.4f}秒"
        else:  # 最后1分钟
            return f"距离抢购还有: {seconds_left:.6f}秒"

    def _should_log_countdown(self, seconds_left):
        """判断是否需要记录倒计时"""
        current_time = time.time()
        
        # 根据剩余时间决定日志记录频率
        if seconds_left > 3600:  # 大于1小时
            log_interval = 300  # 每5分钟记录一次
        elif seconds_left > 600:  # 10分钟-1小时
            log_interval = 60  # 每1分钟记录一次
        elif seconds_left > 60:  # 1-10分钟
            log_interval = 1  # 每秒记录一次
        else:  # 最后1分钟
            log_interval = 0.01  # 每0.01秒记录一次
            
        if current_time - self.last_countdown_log >= log_interval:
            self.last_countdown_log = current_time
            return True
        return False

    def _extract_price_info(self, html_content):
        """提取价格信息"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            price_info = {
                'promotion': None,
                'price': None,
                'sales': None
            }
            
            # 提取促销信息
            promo_element = soup.select_one('span[class*="title"]')
            if promo_element:
                price_info['promotion'] = promo_element.text.strip()
                
            # 提取价格
            price_element = soup.select_one('span[class*="text"]')
            if price_element:
                try:
                    price_info['price'] = float(price_element.text.strip())
                except ValueError:
                    self.logger.warning(f"无法转换价格: {price_element.text}")
                    
            # 提取销量
            sales_element = soup.select_one('div[class*="salesDesc"]')
            if sales_element:
                price_info['sales'] = sales_element.text.strip()
                
            if any(price_info.values()):
                self.logger.debug(f"提取到价格信息: {price_info}")
                return price_info
                
            self.logger.warning("未找到价格信息")
            return None
            
        except Exception as e:
            self.logger.error(f"提取价格信息失败: {str(e)}")
            return None

    async def _save_single_image(self, img: dict, product_id: str) -> dict:
        """保存单个商品图片"""
        try:
            # 从配置文件获取图片保存路径
            base_dir = self.config.get('paths.images', 'data/images')
            os.makedirs(base_dir, exist_ok=True)
            
            # 构建文件名
            filename = f"product_{product_id}_{img['index']}.jpg"
            filepath = os.path.join(base_dir, filename)
            
            # 下载图片
            async with aiohttp.ClientSession() as session:
                async with session.get(img['url']) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        
                        # 保存图片
                        with open(filepath, 'wb') as f:
                            f.write(image_data)
                        
                        file_size = len(image_data)
                        size_kb = file_size / 1024
                        
                        self.logger.info(f"✓ 已保存: {filename} ({size_kb:.1f}KB)")
                        
                        return {
                            'original_url': img['url'],
                            'saved_path': filepath,
                            'type': img['type'],
                            'index': img['index'],
                            'status': 'success',
                            'file_size': file_size,
                            'extract_time': img['extract_time']
                        }
                    else:
                        raise Exception(f"HTTP {response.status}")
                        
        except Exception as e:
            self.logger.error(f"✗ 保存失败: {filename} - {str(e)}")
            return {
                'original_url': img['url'],
                'type': img['type'],
                'index': img['index'],
                'status': 'failed',
                'error': str(e),
                'extract_time': img['extract_time']
            }
  
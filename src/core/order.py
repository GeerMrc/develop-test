from ..utils.logger import Logger
from ..utils.config import Config
from ..exceptions.custom_exceptions import OrderError
import re
import time
import threading
from queue import Queue
import datetime
from ..utils.time_sync import TimeSync

class OrderManager:
    def __init__(self, session):
        """
        初始化订单管理器
        :param session: 登录后的requests session
        """
        self.logger = Logger(__name__)
        self.config = Config()
        self.session = session
        self.queue = Queue(maxsize=100)
        self.success = False
        self.time_sync = TimeSync()

    def parse_url(self, url):
        """解析商品URL，提取必要参数"""
        try:
            # 提取商品ID和SKU ID
            item_id = re.findall(r'id=(\d+)', url)[0]
            sku_id = re.findall(r'skuId=(\d+)', url)
            sku_id = sku_id[0] if sku_id else None
            
            self.logger.debug(f"解析URL - 商品ID: {item_id}, SKU ID: {sku_id}")
            return item_id, sku_id
        except Exception as e:
            self.logger.error(f"URL解析失败: {str(e)}")
            raise OrderError("无效的商品URL")

    def prepare_order(self, url, quantity=1):
        """
        准备订单数据
        :param url: 商品URL
        :param quantity: 购买数量
        """
        try:
            self.logger.info("开始准备订单数据")
            item_id, sku_id = self.parse_url(url)
            
            # 访问商品页面获取必要数据
            response = self.session.get(url)
            if response.status_code != 200:
                raise OrderError("访问商品页面失败")

            # 提取下单所需的关键数据
            self.order_data = self._extract_order_data(response.text, item_id, sku_id, quantity)
            self.logger.info("订单数据准备完成")
            
        except Exception as e:
            self.logger.error(f"准备订单数据失败: {str(e)}")
            raise OrderError(f"准备订单失败: {str(e)}")

    def _extract_order_data(self, html_content, item_id, sku_id, quantity):
        """提取订单所需的关键数据"""
        try:
            # 提取各种token和必要参数
            data = {
                'item_id': item_id,
                'sku_id': sku_id,
                'quantity': quantity,
                # 其他参数根据实际抓包结果添加
            }
            return data
        except Exception as e:
            self.logger.error(f"提取订单数据失败: {str(e)}")
            raise OrderError("订单数据提取失败")

    def submit_order(self, target_time=None):
        """
        提交订单
        :param target_time: 目标抢购时间（可选）
        """
        try:
            if target_time:
                self._wait_for_time(target_time)

            self.logger.info("开始提交订单")
            thread_count = self.config.get('order.thread_count', 80)
            
            # 创建多个线程提高成功率
            threads = []
            for _ in range(thread_count):
                t = threading.Thread(target=self._do_submit_order)
                threads.append(t)
                t.start()

            # 等待所有线程完成
            for t in threads:
                t.join()

            # 检查订单提交结果
            while not self.queue.empty():
                result = self.queue.get()
                if self._check_submit_result(result):
                    self.success = True
                    self.logger.info("订单提交成功!")
                    break

            if not self.success:
                self.logger.warning("订单提交失败")
                raise OrderError("订单提交失败")

        except Exception as e:
            self.logger.error(f"订单提交过程出错: {str(e)}")
            raise OrderError(f"订单提交失败: {str(e)}")

    def _wait_for_time(self, target_time):
        """等待到指定时间（使用服务器时间）"""
        while True:
            # 获取当前服务器时间
            server_time = self.time_sync.get_server_time('taobao')
            if server_time:
                current = server_time.timestamp()
            else:
                # 如果无法获取服务器时间，使用本地时间加偏移
                current = time.time() + self.time_sync.get_time_offset('taobao')
                
            if current >= target_time:
                self.logger.info(f"到达目标时间: {datetime.fromtimestamp(current)}")
                break
            time.sleep(0.01)  # 避免过度占用CPU

    def _do_submit_order(self):
        """实际的订单提交操作"""
        try:
            # 构造订单提交请求
            url = self.config.get('urls.submit_order')
            response = self.session.post(url, data=self.order_data)
            self.queue.put(response.text)
        except Exception as e:
            self.logger.error(f"订单提交请求失败: {str(e)}")

    def _check_submit_result(self, response_text):
        """检查订单提交结果"""
        try:
            # 根据响应内容判断订单是否提交成功
            return '安全链接' in response_text
        except Exception:
            return False 
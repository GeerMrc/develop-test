from datetime import datetime, timedelta
import requests
from ..utils.logger import setup_logger
import time
import json

class TimeSync:
    def __init__(self):
        self.logger = setup_logger('time_sync')
        self._time_offset = {}  # 存储不同服务器的时间偏移
        self._last_sync = {}    # 存储最后同步时间
        self._sync_interval = 300  # 5分钟同步一次
        self._last_sync_time = None  # 上次同步时间
        self._cached_offset = 0.0    # 缓存的时间偏移
        
        # 服务器时间API
        self.time_api = {
            'taobao': 'https://api.m.taobao.com/rest/api3.do?api=mtop.common.getTimestamp',
            'jd': 'https://a.jd.com//ajax/queryServerData.html',
            'system': None  # 使用系统时间
        }

    def get_server_time(self, platform='taobao'):
        """获取服务器时间，增加重试机制和时区处理"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                urls = {
                    'taobao': "https://www.taobao.com",
                    'jd': "https://www.jd.com"
                }
                
                url = urls.get(platform.lower())
                if not url:
                    raise ValueError(f"Unsupported platform: {platform}")
                    
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                server_date_str = response.headers['Date']
                # 解析UTC时间
                server_time = datetime.strptime(server_date_str, '%a, %d %b %Y %H:%M:%S %Z')
                # 转换为本地时间
                local_time = server_time + timedelta(hours=8)  # 转换为北京时间
                
                self.logger.debug(f"{platform.upper()} Server Time (Local): {local_time}")
                if local_time:
                    self._last_sync_time = datetime.now()
                    return local_time
                    
            except requests.RequestException as e:
                self.logger.error(f"Error fetching {platform} server time: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(1)

    def get_time_offset(self, platform='taobao', force_sync=False):
        """获取时间偏移，增加缓存机制"""
        now = datetime.now()
        
        # 如果距离上次同步时间不足5分钟且不强制同步，使用缓存的偏移值
        if (not force_sync and self._last_sync_time and 
            (now - self._last_sync_time).total_seconds() < self._sync_interval):
            return float(self._cached_offset)
            
        server_time = self.get_server_time(platform)
        if not server_time:
            return float(self._cached_offset)
            
        # 计算时间偏移并确保是浮点数
        self._cached_offset = float((server_time - now).total_seconds())
        self._last_sync_time = now
        
        return self._cached_offset
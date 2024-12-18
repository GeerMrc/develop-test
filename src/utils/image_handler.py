import os
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime
from ..utils.logger import setup_logger
from ..utils.config import Config

class ImageHandler:
    def __init__(self):
        """初始化图片处理器"""
        self.logger = setup_logger('image_handler')
        self.config = Config()
        
        # 从配置文件加载设置
        storage_config = self.config.get('storage.images', {})
        self.save_path = storage_config.get('path', 'data/images')
        self.allowed_formats = storage_config.get('formats', ['jpg', 'webp', 'png'])
        self.quality = storage_config.get('quality', 95)
        self.max_size = storage_config.get('max_size', 10 * 1024 * 1024)  # 默认10MB
        
        # 确保保存目录存在
        os.makedirs(self.save_path, exist_ok=True)
        
    def _generate_filename(self, url, product_id):
        """生成图片文件名"""
        hash_name = hashlib.md5(url.encode()).hexdigest()
        return f"{product_id}_{hash_name}"
        
    async def download_and_save(self, url, product_id):
        """下载并保存图片"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # 读取图片数据
            image = Image.open(BytesIO(response.content))
            
            # 生成文件名
            filename = self._generate_filename(url, product_id)
            
            # 保存不同格式
            saved_files = []
            for fmt in self.allowed_formats:
                try:
                    fmt = fmt.lower()  # 统一使用小写格式
                    save_path = os.path.join(self.save_path, f"{filename}.{fmt}")
                    
                    # 转换图片格式
                    if image.mode in ('RGBA', 'P'):
                        converted_image = image.convert('RGB')
                    else:
                        converted_image = image
                    
                    # 根据不同格式选择保存参数
                    save_kwargs = {
                        'quality': self.quality
                    }
                    
                    if fmt == 'jpg' or fmt == 'jpeg':
                        save_kwargs['format'] = 'JPEG'
                    elif fmt == 'png':
                        save_kwargs['format'] = 'PNG'
                    elif fmt == 'webp':
                        save_kwargs['format'] = 'WEBP'
                    else:
                        self.logger.warning(f"不支持的图片格式: {fmt}")
                        continue
                    
                    # 保存图片
                    converted_image.save(save_path, **save_kwargs)
                    saved_files.append(save_path)
                    self.logger.debug(f"成功保存图片: {save_path}")
                    
                except Exception as e:
                    self.logger.error(f"保存 {fmt} 格式失败: {str(e)}")
                    continue
            
            if not saved_files:
                raise Exception("没有成功保存任何格式的图片")
            
            return saved_files
            
        except Exception as e:
            self.logger.error(f"图片下载保存失败: {str(e)}")
            return None
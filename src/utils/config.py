import yaml
import os

class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'config'):
            self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            # 优先使用环境变量中的配置路径（用于测试）
            config_path = os.environ.get('CONFIG_PATH')
            if not config_path:
                config_path = os.path.join('config', 'config.yaml')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            self.config = {}
            print(f"加载配置文件失败: {str(e)}")
    
    def get(self, key, default=None):
        """获取配置值"""
        try:
            keys = key.split('.')
            value = self.config
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    return default
            return value if value is not None else default
        except Exception:
            return default
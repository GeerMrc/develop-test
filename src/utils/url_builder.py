from typing import Dict, Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from collections import OrderedDict

class URLBuilder:
    """URL 构建工具"""
    
    @staticmethod
    def build_product_url(base_url: str, params: Dict[str, str]) -> str:
        """
        构建商品 URL，保持参数固定顺序：原有参数 -> id -> skuId
        
        Args:
            base_url: 基础URL (包含已有参数，如 _u)
            params: 要添加的参数 (e.g., {"id": "xxx", "skuId": "xxx"})
            
        Returns:
            str: 完整的商品URL
        """
        # 解析基础URL
        parsed = urlparse(base_url)
        
        # 获取现有参数
        ordered_params = OrderedDict(parse_qs(parsed.query))
        ordered_params = {k: v[0] for k, v in ordered_params.items()}
        
        # 添加商品参数
        if 'id' in params:
            ordered_params['id'] = params['id']
        if 'skuId' in params:
            ordered_params['skuId'] = params['skuId']
        
        # 构建查询字符串
        query = urlencode(ordered_params)
        
        # 重建URL
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{query}"
    
    @staticmethod
    def build_tmall_url(product_id: str, sku_id: Optional[str] = None, extra_params: Dict[str, str] = None) -> str:
        """
        构建天猫商品URL
        
        Args:
            product_id: 商品ID
            sku_id: SKU ID (可选)
            extra_params: 额外参数 (可选)
            
        Returns:
            str: 完整的天猫商品URL
        """
        base_url = "https://chaoshi.detail.tmall.com/item.htm"
        params = {"id": product_id}
        
        if sku_id:
            params["skuId"] = sku_id
            
        if extra_params:
            params.update(extra_params)
            
        return URLBuilder.build_product_url(base_url, params) 
import json
from datetime import datetime
from typing import Dict, Any

class ResultFormatter:
    """结果格式化工具"""
    
    @staticmethod
    def format_test_result(
        browser_type: str,
        browser_info: Dict[str, Any],
        product_info: Dict[str, Any],
        server_time: datetime,
        time_offset: float,
        url: str,
        performance_metrics: Dict[str, float] = None,
        test_status: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """格式化测试结果"""
        
        # 基础性能指标
        if performance_metrics is None:
            performance_metrics = {
                "page_load_time": None,
                "parse_time": None,
                "total_time": None
            }
            
        # 测试状态
        if test_status is None:
            test_status = {
                "success": product_info is not None,
                "fields_found": {
                    "title": product_info.get('title') is not None if product_info else False,
                    "price": product_info.get('price_info') is not None if product_info else False,
                    "target_time": product_info.get('target_time') is not None if product_info else False,
                    "images": len(product_info.get('images', [])) > 0 if product_info else False
                },
                "errors": [],
                "warnings": []
            }
            
        return {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "product_id": product_info.get('product_id'),
                "url": url,
                "test_type": "browser_test"
            },
            "browser_info": {
                "type": browser_type,
                "headless": browser_info.get('headless', True),
                "user_agent": browser_info.get('user_agent'),
                "viewport": browser_info.get('viewport')
            },
            "timing": {
                "local_time": datetime.now().isoformat(),
                "server_time": server_time.isoformat(),
                "time_offset": time_offset,
                "performance": performance_metrics
            },
            "product_data": {
                "basic_info": {
                    "title": product_info.get('title'),
                    "price": product_info.get('price_info', {}).get('price'),
                    "promotion": product_info.get('price_info', {}).get('promotion'),
                    "sales": product_info.get('price_info', {}).get('sales')
                },
                "timing": {
                    "target_time": product_info.get('target_time'),
                    "timestamp": product_info.get('timestamp')
                },
                "resources": {
                    "images": [
                        {
                            "index": img.get('index'),
                            "type": img.get('type'),
                            "status": img.get('status'),
                            "original_url": img.get('original_url'),
                            "saved_path": img.get('saved_path'),
                            "file_size": f"{img.get('file_size', 0) / 1024:.1f}KB",
                            "extract_time": img.get('extract_time')
                        }
                        for img in product_info.get('images', [])
                    ]
                }
            },
            "test_results": test_status
        }
    
    @staticmethod
    def save_result(data: Dict[str, Any], file_path: str) -> None:
        """保存结果到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2) 
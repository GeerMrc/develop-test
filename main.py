from src.core.login import LoginManager
from src.core.order import OrderManager
from src.core.product import ProductManager
from src.utils.config import Config
import asyncio
import time
from datetime import datetime

async def main():
    config = Config()
    login_manager = LoginManager()
    
    try:
        # 登录
        await login_manager.login()
        if not login_manager.check_login_status():
            print("登录失败!")
            return

        # 构建商品URL
        product_config = config.get('urls.product.maotai')
        target_url = f"{product_config['url']}?id={product_config['id']}&skuId={product_config['sku_id']}"
        
        product_manager = ProductManager(login_manager.session)
        product_info = await product_manager.start_monitoring(target_url)

        # 初始化订单管理器
        order_manager = OrderManager(login_manager.session)
        
        # 准备订单数据
        quantity = config.get('order.quantity', 1)
        order_manager.prepare_order(target_url, quantity=quantity)
        
        # 使用获取到的抢购时间
        order_manager.submit_order(product_info['timestamp'])
        
        # 停止商品监控
        await product_manager.stop_monitoring()
        
    except Exception as e:
        print(f"程序执行失败: {str(e)}")
    finally:
        # 确保清理资源
        if 'product_manager' in locals():
            await product_manager.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main()) 
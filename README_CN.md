# 天猫商品信息抓取工具

基于 Python 的商品信息监控与抓取系统，支持多浏览器测试和自动化操作。

## 功能特性

- 多浏览器支持 (Chrome、Firefox、WebKit)
- 无头/界面模式可选
- 商品信息自动提取
- 服务器时间同步
- 图片资源管理
- 详细的日志记录
- 性能监控
- 测试结果报告

## 安装说明

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/tmall-product-information-scraper.git
cd tmall-product-information-scraper
```

2. 安装依赖：
```bash
pip install -r requirements.txt
playwright install
```

3. 配置浏览器和商品设置：
```bash
cp config/config.yaml.example config/config.yaml
# 编辑 config.yaml 设置浏览器和商品配置
```

4. 运行测试：
```bash
pytest tests/test_live.py -v
```

## 项目结构
```
tmall/
├── src/
│   ├── core/           # 核心功能模块
│   ├── utils/          # 工具类
│   └── browser/        # 浏览器管理
├── tests/              # 测试用例
├── config/             # 配置文件
├── data/               # 数据存储
│   ├── images/         # 商品图片
│   └── results/        # 测试结果
└── logs/               # 日志文件
```

## 主要功能模块
1. 商品信息管理 (ProductManager)
   - 商品详情提取
   - 图片资源下载
   - 价格监控

2. 时间同步 (TimeSync)
   - 服务器时间获取
   - 本地时间校准
   - 倒计时管理

3. 订单管理 (OrderManager)
   - 订单创建
   - 状态跟踪
   - 结果验证

## 开发状态
最后更新：2024-01-18 17:52

- [x] 基础框架搭建
- [x] 多浏览器支持
- [x] 商品信息提取
- [x] 图片资源处理
- [x] 日志系统完善
- [ ] Web控制界面
- [ ] 抢购功能优化
- [ ] 性能优化

## 贡献指南
请查看 [Rules_CN.md](Rules_CN.md) 了解详细的开发规范和贡献指南。

## 许可证
MIT License 
# Tmall Product Information Scraper

A tool for scraping and monitoring product information from Tmall/Taobao, with multi-browser support and automated testing capabilities.

## Features

- Multi-browser support (Chrome, Firefox, WebKit)
- Headless/UI mode options
- Product information extraction
- Server time synchronization
- Image downloading and management
- Detailed logging and debugging
- Performance monitoring
- Test result reporting

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tmall-product-information-scraper.git
cd tmall-product-information-scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
playwright install
```

3. Configure the browser and product settings:
```bash
cp config/config.yaml.example config/config.yaml
# Edit config.yaml to set browser and product configuration
```

4. Run tests:
```bash
pytest tests/test_live.py -v
```

## Project Structure
```
tmall/
├── src/
│   ├── core/           # Core functionality modules
│   ├── utils/          # Utility classes
│   └── browser/        # Browser management
├── tests/              # Test cases
├── config/             # Configuration files
├── data/               # Data storage
│   ├── images/         # Product images
│   └── results/        # Test results
└── logs/               # Log files
```

## Main Functionality Modules
1. Product Information Management (ProductManager)
   - Product detail extraction
   - Image resource downloading
   - Price monitoring

2. Time Synchronization (TimeSync)
   - Server time retrieval
   - Local time calibration
   - Countdown management

3. Order Management (OrderManager)
   - Order creation
   - Status tracking
   - Result verification

## Development Status
Last updated: 2024-01-18 17:52

- [x] Basic framework setup
- [x] Multi-browser support
- [x] Product information extraction
- [x] Image resource processing
- [x] Logging system improvement
- [ ] Web control interface
- [ ] Purchase function optimization
- [ ] Performance optimization

## Contribution Guidelines
Please refer to [Rules.md](Rules.md) for detailed development guidelines and contribution guidelines.

## License
MIT License
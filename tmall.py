import re, time, random, datetime, sys, requests, threading, psutil
from requests.cookies import RequestsCookieJar
from selenium.webdriver.common.by import By
from multiprocessing import Queue
from urllib.parse import quote
from selenium import webdriver
from io import BytesIO
from PIL import Image
import time


# 输入触发时间 返回时间戳
def postTime(setTime):
    # 转换成时间数组
    timeArray = time.strptime(setTime, "%Y/%m/%d %H:%M:%S")
    # 转换成时间戳
    timestamp = time.mktime(timeArray)
    return timestamp

class Login():
    def __init__(self):
        # 设置关键词进行匹配或判断，下同
        self.key_word1 = '账号管理'
        self.key_word2 = '安全链接'
        self.j = 0
        # 创建队列存放post订单结果
        self.queue = Queue(maxsize=100)
        # 创建Session对象  requests库的session对象会在同一个session实例的所有请求之间使用cookies保持登录状态
        self.session = requests.session()
        # 设置headers
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.50"
        self.headers = {
            'User-Agent': ua
        }
        self.session.headers.update(self.headers)

    # 扫码登录，获取cookies
    def get_cookies(self):
        options = webdriver.ChromeOptions()
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument('--headless')
        browser = webdriver.Chrome(options=options)
        url = 'https://login.taobao.com/member/login.jhtml'
        browser.get(url)
        # 点击跳转扫码界面
        browser.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[3]/div/div/div/div[1]/i').click()
        time.sleep(round(random.uniform(1, 2), 2))
        # 获取并保存二维码截图
        qrcode_img_data = browser.find_element(By.XPATH, '//*[@id="login"]/div[2]/div/div[1]/div[1]').screenshot_as_png
        qrcode_img = Image.open(BytesIO(qrcode_img_data))
        qrcode_img.save('qrcode.png')
        qrcode_img.show()
        print("请扫码登录！")
        time.sleep(2)
        # 每隔1.5秒判断一次是否登录成功
        t = 0
        while t < 40:
            try:
                info = browser.find_element(By.XPATH,
                                            '//*[@id="J_Col_Main"]/div/div[1]/div/div[1]/div[1]/div/div[1]/a/em').text
                print('您的帐户:' + info)
                for proc in psutil.process_iter():  # 遍历当前process
                    if proc.name() == "Microsoft.Photos.exe":
                        proc.kill()  # 关闭该process
                break
            except:
                time.sleep(1.5)
                t += 1
        # 获取Cookie并保持在session中
        cookies = browser.get_cookies()
        time.sleep(round(random.uniform(1, 2), 2))
        browser.quit()
        selenium_cookies = cookies
        tmp_cookies = RequestsCookieJar()
        for item in selenium_cookies:
            tmp_cookies.set(item["name"], item["value"])
        self.session.cookies.update(tmp_cookies)

    # 登录
    def login(self):
        print("登录中...")
        try:
            req = self.session.get('https://i.taobao.com/user/baseInfoSet.htm?').text
            if self.key_word1 in req:
                print("自动登录成功！")
            else:
                print("自动登录失败！\n请再次扫码登录！")
                self.get_cookies()
                self.session.get('https://i.taobao.com/user/baseInfoSet.htm?').text
                if self.key_word1 in req:
                    print("自动登录成功！")
                else:
                    print("自动登录失败！\n请手动完成该任务")
                    sys.exit(0)
        except:
            print('程序出错！')
            sys.exit(0)

    # 提交订单
    def submitOrder(self, url, skuId, setTime, quantity):
        self.url = url
        quantity = '_' + quantity + '_'
        # 获取cookies并登录
        self.cookies = self.get_cookies()
        self.login()
        time.sleep(round(random.uniform(1, 2), 2))
        # 进入商品详情页
        self.req = self.session.get(url=self.url).text
        time.sleep(round(random.uniform(1, 2), 2))
        # 提取 key datas
        self.patterGoods()
        time.sleep(round(random.uniform(1, 2), 2))

        # 确认订单
        data = {
            "buy_param": self.auction[0] + quantity + skuId
        }
        url = 'https://buy.tmall.com/order/confirm_order.htm?x-itemid=' + self.auction[0] + '&x-uid=' + self.userId[0]
        k = 0
        while True:
            print("\r购买倒计时：%.3f" % (setTime - time.time()), end="", flush=True)
            if (time.time() >= setTime):
                print('\n')
                print(datetime.datetime.now())
                while True:
                    self.req = self.session.post(url=url, data=data).text
                    # 获取数据
                    key = self.patterData()
                    k += 1
                    if (k == 50):
                        print("\n确认订单失败！下次加油哦")
                        print(datetime.datetime.now())
                        sys.exit(0)
                    if (key):
                        print("\n确认订单成功！")
                        print(datetime.datetime.now())
                        break
                break

        # 提交订单
        data = {
            "endpoint": self.endpoint,
            "linkage": self.linkage,
            "data": self.data,
            "action": self.action,
            "_tb_token_": self.tbToken,
            "event_submit_do_confirm": self.event,
            "praper_alipay_cashier_domain": self.unitSuffix,
            "input_charset": self.charset,
            "hierarchy": self.hierarchy
        }
        url = 'https://buy.tmall.com/auction/confirm_order.htm?x-itemid=' + self.auction[0] + '&x-uid=' + self.userId[
            0] + '&submitref=' + self.submitUrl
        # 多线程，提高抢购效率
        thread_list = []
        for i in range(1, 80):
            t = threading.Thread(target=self.post, args=(url, data))
            thread_list.append(t)
        l = len(thread_list)
        # 启动线程
        for i in range(0, l - 1):
            thread_list[i].start()
        # 关闭线程
        for t in range(0, l - 1):
            thread_list[i].join()
        while self.queue.empty() == False:
            req = self.queue.get()
            if self.key_word2 in req:
                print('提交订单成功！请快尽快付款！')
                self.j = 1
                break
        if self.j == 0:
            print('提交订单失败！请下次重试！')
        print('Buy End!')
        sys.exit(0)

    # 提取信息：商品详情
    def patterGoods(self):
        # 页面id
        self.auction = re.findall(r'(?<=auction=).*?(?=&)', self.req)
        # 用户id
        self.userId = re.findall(r'(?<=&userid=).*?(?=&)', self.req)
        # 购买端token
        tbTokens = re.findall(r'(?<=yunid=&).*?(?=&)', self.req)
        self.tbToken = tbTokens[0]

    # 提取信息：生成订单数据
    def patterData(self):
        # 正则匹配
        data = re.findall(r'(?<="secretValue":).*?(?=,"unitSuffix")', self.req)
        if not data:
            return False
        self.submitUrl = ''.join(data)
        self.submitUrl = re.sub(r'"', '', self.submitUrl)
        self.submitUrl = re.sub(r',', '&', self.submitUrl)
        self.submitUrl = re.sub(r':', '=', self.submitUrl)

        data = re.findall(r'(?<="endpoint":).*?(?=,"data")', self.req)
        self.endpoint = ''.join(data)
        self.endpoint = quote(self.endpoint)

        data = re.findall(r'(?<="action":").*?(?=","event_submit_do_confirm")', self.req)
        self.action = ''.join(data)
        data = re.findall(r'(?<="event_submit_do_confirm":").*?(?=","input_charset")', self.req)
        self.event = ''.join(data)
        data = re.findall(r'(?<="input_charset":").*?(?=","pcSubmitUrl")', self.req)
        self.charset = ''.join(data)
        data = re.findall(r'(?<="unitSuffix":").*?(?="}},)', self.req)
        unitSuffix = ''.join(data)
        self.unitSuffix = "cashier" + unitSuffix

        data = re.findall(r'(?<="data":).*?(?=,"linkage")', self.req)
        self.data = ''.join(data)
        self.data = quote(self.data)  # url 编码

        data = re.findall(r'(?<="linkage":).*?(?=,"hierarchy")', self.req)
        self.linkage = ''.join(data)
        self.linkage = quote(self.linkage)

        data = re.findall(r'(?<="hierarchy":).*?(?=,"container")', self.req)
        self.hierarchy = ''.join(data)
        self.hierarchy = quote(self.hierarchy)
        return True

    def post(self, url, data):
        req = self.session.post(url=url, data=data).text
        self.queue.put(req)


from TTime import postTime
import TbMoudle, time

if __name__ == "__main__":
    # 商品链接
    # url = 'https://detail.tmall.com/item.htm?id=576148466933&spm=a1z09.2.0.0.28032e8dcv63yd&_u=1340hb4c2d7d&skuId=4516861399500'            #用来测试的淘宝链接，通过
    url = 'https://chaoshi.detail.tmall.com/item.htm?id=20739895092&spm=a1z0k.7628870.0.0.6d8537de1tkYdk&_u=t2dmg8j26111&skuId=4227830352490'  # 茅台链接
    # url = 'https://chaoshi.detail.tmall.com/item.htm?spm=a1z0d.6639537/tb.1997196601.3.52367484NWZmwA&id=541462757234&skuId=5029227863773'            #用来测试的天猫链接，通过
    '''
    #设定抢购物品的url
    #详情页网址是用电脑登录，选好数量和样式之后的网址
    url=str(input("请输入详情页网址:\n"))
    '''

    # 仅适用于 skUid 在链接末  即已选好商品规格的链接
    skuIds = url.split('=')
    k = len(skuIds) - 1
    skuId = skuIds[k]
    quantity = '1'  # 购买数量

    # 定时 + 毫秒延迟校正
    action_time = '20:00:00'
    post_date = time.strftime("%Y/%#m/%#d", time.localtime(time.time()))
    post_time = post_date + ' ' + action_time
    setTime = postTime(post_time) - 0.2

    # 实例化对象
    a = TbMoudle.Login()
    a.submitOrder(url, skuId, setTime, quantity)

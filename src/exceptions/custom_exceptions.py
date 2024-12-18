class TmallBotException(Exception):
    """基础异常类"""
    pass

class LoginError(TmallBotException):
    """登录相关错误"""
    pass

class OrderError(TmallBotException):
    """订单相关错误"""
    pass

class BrowserError(TmallBotException):
    """浏览器相关错误"""
    pass

class ProductError(TmallBotException):
    """商品相关错误"""
    pass 
"""routers 子包：把业务域拆到这里，主类用 include_router 注册。"""
from .web import WebRouter

__all__ = ["WebRouter"]

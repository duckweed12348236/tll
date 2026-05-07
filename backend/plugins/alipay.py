from typing import Any

from plugins import Singleton
from config import ALIPAY_APPID, ALIPAY_PRIVATE_KEY, ALIPAY_PUBLIC_KEY
import alipay


class Alipay(Singleton):
    def __init__(self) -> None:
        self.instance = alipay.AliPay(
            appid=ALIPAY_APPID,
            app_notify_url=None,
            app_private_key_string=ALIPAY_PRIVATE_KEY,
            alipay_public_key_string=ALIPAY_PUBLIC_KEY,
            debug=True,
            verbose=True
        )

    def pay(self, order_id: str, amount: str, subject: str, notify_url: str | None = None) -> str:
        return self.instance.api_alipay_trade_app_pay(
            out_trade_no=order_id,
            subject=subject,
            total_amount=amount,
            notify_url=notify_url
        )

    def verify(self, data: dict[str, Any], sign: str) -> bool:
        return self.instance.verify(data, sign)

from alibabacloud_dypnsapi20170525.client import Client
from alibabacloud_tea_openapi.models import Config
from alibabacloud_dypnsapi20170525.models import SendSmsVerifyCodeRequest
from alibabacloud_tea_util.models import RuntimeOptions
from loguru import logger

from plugins import Singleton
from config import ALIYUN_SMS_CODE_ACCESS_KEY_ID, ALIYUN_SMS_CODE_ACCESS_KEY_SECRET


class AliyunSmsCodeSender(Singleton):
    def __init__(self):
        self.client = Client(
            Config(
                access_key_id=ALIYUN_SMS_CODE_ACCESS_KEY_ID,
                access_key_secret=ALIYUN_SMS_CODE_ACCESS_KEY_SECRET,
                endpoint="dypnsapi.aliyuncs.com"
            )
        )
        self.runtime = RuntimeOptions()

    async def send(self, telephone: str | int, code: int | str) -> None:
        request = SendSmsVerifyCodeRequest(
            sign_name='速通互联验证码',
            template_code='100001',
            phone_number=str(telephone),
            template_param=str({"code": code, "min": "4"})
        )
        try:
            await self.client.send_sms_verify_code_with_options_async(request, self.runtime)
        except Exception as error:
            logger.error(error)

# import socket
#
# from consul import Consul, Check
# from uuid import uuid4
# from config import CONSULT_CONFIG, SERVER_CONFIG
# from plugins import Plugin
#
#
# class ConsulManager(Plugin):
#     def __init__(self) -> None:
#         self.client = Consul(host=CONSULT_CONFIG["host"], port=CONSULT_CONFIG["port"])
#         self.service_id = uuid4().hex
#
#     def init(self) -> None:
#         with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
#             s.connect(("8.8.8.8", 80))
#             local_ip = s.getsockname()[0]
#         self.client.agent.service.register(
#             name="tll-server",
#             service_id=self.service_id,
#             address=local_ip,
#             port=SERVER_CONFIG["port"],
#             check=Check.http(f"http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}/check", "20s")
#         )
#
#     def close(self) -> None:
#         self.client.agent.service.deregister(self.service_id)

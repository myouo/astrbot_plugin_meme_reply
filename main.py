import os
import random

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.message_components import At, Poke, Reply
from astrbot.api.star import Context, Star, register


ASSETS_DIR = os.path.join(os.path.dirname(__file__), \"assets\")
IMAGE_EXTS = {\".jpg\", \".jpeg\", \".png\", \".gif\", \".webp\", \".bmp\"}


def _list_images(character: str) -> list[str]:
    \"\"\"返回角色目录下所有图片的绝对路径列表。\"\"\"
    char_dir = os.path.join(ASSETS_DIR, character)
    if not os.path.isdir(char_dir):
        return []
    return [
        os.path.join(char_dir, f)
        for f in os.listdir(char_dir)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTS
    ]


def _random_image(character: str) -> str | None:
    \"\"\"从角色目录中随机选取一张图片路径，无图片时返回 None。\"\"\"
    images = _list_images(character)
    return random.choice(images) if images else None


@register(
    \"astrbot_plugin_meme_reply\",
    \"myouo\",
    \"使用表情包回复 @、拍一拍、回复等操作\",
    \"1.3.0\",
)
class MemeReplyPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None) -> None:
        super().__init__(context)
        self.config = config or {}

    async def initialize(self) -> None:
        # 确保 assets 目录存在
        os.makedirs(ASSETS_DIR, exist_ok=True)
        # 从 KV 存储读取当前角色，回退到配置默认值
        default = self.config.get(\"default_character\", \"default\")
        self._character: str = await self.get_kv_data(\"character\", default)
        logger.info(f\"[meme_reply] 当前角色: {self._character}\")

    def _is_plugin_admin(self, user_id: str) -> bool:
        \"\"\"判断用户是否在插件管理员列表中。\"\"\"
        admins: list = self.config.get(\"admins\", [])
        return str(user_id) in [str(a) for a in admins]

    async def _send_meme(self, event: AstrMessageEvent) -> None:
        \"\"\"随机发送一张当前角色的表情包。\"\"\"
        img_path = _random_image(self._character)
        if img_path is None:
            logger.warning(
                f\"[meme_reply] 角色 '{self._character}' 下没有图片，跳过发送。\"
            )
            return
        yield event.image_result(img_path)

    # -------------------------------------------------------------------------
    # /meme <character> 指令：切换角色
    # -------------------------------------------------------------------------
    @filter.command(\"meme\")
    async def cmd_meme(self, event: AstrMessageEvent):
        \"\"\"切换表情包角色。用法: /meme <角色名>  仅插件管理员可用。\"\"\"
        sender_id = event.get_sender_id()
        if not self._is_plugin_admin(sender_id):
            yield event.plain_result(\"你没有权限使用该指令。\")
            return

        args = event.message_str.strip().split()
        # args[0] 是命令本身（meme），args[1] 是角色名
        if len(args) < 2:
            chars = _list_characters()
            yield event.plain_result(
                f\"用法: /meme <角色名>\
当前可用角色: {', '.join(chars) or '(无)'}\
当前角色: {self._character}\"
            )
            return

        character = args[1]
        char_dir = os.path.join(ASSETS_DIR, character)
        if not os.path.isdir(char_dir):
            chars = _list_characters()
            yield event.plain_result(
                f\"角色 '{character}' 不存在。可用角色: {', '.join(chars) or '(无)'}\"
            )
            return

        self._character = character
        await self.put_kv_data(\"character\", character)
        yield event.plain_result(f\"已切换角色为: {character}\")

    # -------------------------------------------------------------------------
    # 监听所有消息，检测 @bot、被回复、被拍一拍
    # -------------------------------------------------------------------------
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        \"\"\"监听所有消息，识别 @bot / 回复bot / 拍一拍bot 并回复表情包。\"\"\"
        raw = event.message_obj
        self_id = str(raw.self_id)
        message = event.get_messages()

        triggered = False
        poke_sender_id: str | None = None

        for seg in message:
            # 被 @ —— At 组件的 qq 字段等于 bot 自身 ID
            if isinstance(seg, At) and str(seg.qq) == self_id:
                triggered = True
                break

            # 被回复 —— Reply 组件的 sender_id 等于 bot 自身 ID
            if isinstance(seg, Reply) and str(getattr(seg, \"sender_id\", \"\")) == self_id:
                triggered = True
                break

            # 被拍一拍 —— Poke 组件，id 是被戳的人（bot）
            if isinstance(seg, Poke) and str(seg.id) == self_id:
                triggered = True
                poke_sender_id = str(raw.sender.user_id)
                break

        if not triggered:
            return

        # 如果是拍一拍，先拍回去
        if poke_sender_id is not None:
            try:
                bot = event.bot  # AiocqhttpMessageEvent 暴露了 bot 属性
                group_id = getattr(raw, \"group_id\", None)
                if group_id:
                    await bot.call_action(
                        \"group_poke\",
                        group_id=int(group_id),
                        user_id=int(poke_sender_id),
                    )
                else:
                    await bot.call_action(
                        \"friend_poke\",
                        user_id=int(poke_sender_id),
                    )
            except Exception as e:
                logger.warning(f\"[meme_reply] 发送拍一拍失败: {e}\")

        # 发送表情包
        async for result in self._send_meme(event):
            yield result

    async def terminate(self) -> None:
        pass


def _list_characters() -> list[str]:
    \"\"\"列出 assets 下所有角色文件夹名。\"\"\"
    if not os.path.isdir(ASSETS_DIR):
        return []
    return [
        d
        for d in os.listdir(ASSETS_DIR)
        if os.path.isdir(os.path.join(ASSETS_DIR, d))
    ]

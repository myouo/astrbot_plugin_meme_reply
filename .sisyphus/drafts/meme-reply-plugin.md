# Draft: astrbot_plugin_meme_reply

## Requirements (confirmed)
- 插件接收 bot 动作：@、拍一戳(poke/nudge)、回复
- 被 @ → 回复表情包（从 assets 文件夹随机选图）
- 被拍一戳 → 先拍回去 → 再回复表情包
- 被回复 → 回复表情包
- assets 文件夹结构：每个子文件夹 = 一个角色/种类
- 插件管理员可以使用 `/meme charc` 切换使用的角色文件夹
- 用户可以自定义上传表情包到对应子文件夹
- 平台：aiocqhttp（OneBot v11 协议）

## Technical Decisions
- 框架：AstrBot 插件系统（Python，继承 Star 类）
- 注册方式：@register 装饰器 + metadata.yaml
- 事件处理：@filter.event_message_type(ALL) 监听所有消息，解析消息链中的 At/Reply/Poke 组件
- 配置：_conf_schema.json 定义插件管理员列表和默认角色
- 持久化：使用 self.put_kv_data / get_kv_data 存储当前角色选择
- 图片发送：Comp.Image.fromFileSystem() 从本地路径发送
- 随机选图：random.choice() 从角色目录中选取图片文件

## Research Findings
- aiocqhttp 的 Poke 事件：sub_type == "poke", target_id 字段
- At 组件：Comp.At(qq=xxx) 在消息链中
- Reply 组件：Comp.Reply(id=xxx) 在消息链中，含 sender_id 可判断是否回复 bot
- 发送 Poke 回去：通过 bot.call_action("send_poke", user_id=xxx, group_id=xxx) 或消息链中添加 Comp.Poke
- self_id 可通过 event.message_obj.self_id 获取 bot 自身 ID
- 插件数据目录：get_astrbot_data_path() / "plugin_data" / self.name

## Open Questions
- 拍一戳(poke) 发送方式确认：是用消息链 Comp.Poke 还是 call_action？
- 插件管理员定义：AstrBot 自带 admin 权限系统 vs 插件自定义管理员列表？
- assets 目录下的默认角色文件夹名：用什么命名？

## Scope Boundaries
- INCLUDE: 核心事件监听、表情包回复、/meme 指令组、assets 文件夹管理
- INCLUDE: 插件管理员机制、角色切换、随机选图
- EXCLUDE: 表情包在线下载/抓取
- EXCLUDE: 多平台适配（仅 aiocqhttp）
- EXCLUDE: 表情包编辑/制作功能

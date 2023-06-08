<p align="center">
  <a href="https://v2.nonebot.dev/"><img src="https://v2.nonebot.dev/logo.png" width="200" height="200" alt="nonebot-adapter-villa"></a>
</p>

<div align="center">

# NoneBot-Adapter-Villa

_✨ 大别野 协议适配 ✨_

<img src="https://img.shields.io/pypi/v/nonebot-adapter-villa" alt="version">
<img src="https://img.shields.io/badge/Python-3.8+-yellow" alt="python">
<a href="https://cdn.jsdelivr.net/gh/CMHopeSunshine/nonebot-adapter-villa@master/LICENSE"><img src="https://img.shields.io/github/license/CMHopeSunshine/nonebot-adapter-villa" alt="license"></a>

</div>

## 安装

在`NoneBot2`项目目录下使用脚手架安装：

```
nb adapter install nonebot-adapter-villa
```

## 配置

修改 NoneBot 配置文件 `.env` 或者 `.env.*`。

### Driver

本适配器同时需要`ReverseDriver`和`ForwardDriver`，参考 [driver](https://v2.nonebot.dev/docs/next/advanced/driver#%E9%A9%B1%E5%8A%A8%E5%99%A8%E7%B1%BB%E5%9E%8B) 配置项。

例如：

```dotenv
DRIVER=~fastapi+~httpx
```

### VILLA_BOTS

配置机器人帐号列表，每个bot有3个必填配置，在大别野官方机器人开发者社区(别野ID: OpenVilla)申请时获得，

- bot_id: 机器人id，以`bot_`开头
- bot_secret: 机器人密钥
- callback_url: http回调地址，例如申请bot时给的回调地址是`http://域名/your/callback/url`，那么配置里的`callback_url`填写`/your/callback/url`
  例如：

```dotenv
VILLA_BOTS='
[
  {
    "bot_id": "bot_123456789",
    "bot_secret": "abc123def456",
    "callback_url": "/your/callback/url"
  }
]
'
```

## 示例

### 消息段展示

以下是一个简单的插件示例，展示各种消息段：

```python
from nonebot import on_command
from nonebot.params import CommandArg

from nonebot.adapters.villa import Bot, SendMessageEvent, Message, MessageSegment

matcher = on_command('发送')

@matcher.handle()
async def matcher_handler(bot: Bot, event: SendMessageEvent, cmd_arg: Message = CommandArg()):
    msg = Message()
    args = cmd_arg.extract_plain_text().strip().split(' ')
    for arg in args:
        if arg == "艾特我":
            msg += MessageSegment.mention_user(event.villa_id, event.from_user_id)
        elif arg == "艾特bot":
            msg += MessageSegment.mention_robot(bot.self_id, bot.nickname)
        elif arg == "文字":
            msg += MessageSegment.text("文字")
            # 表情也是用text来发送，以[表情名]格式，例如MessageSegment.text("[爱心]")
        elif arg == "房间":
            msg += MessageSegment.room_link(event.villa_id, event.room_id)
        elif arg == "链接":
            msg += MessageSegment.link("https://www.miyoushe.com/ys/article/39670307", show_text="这是链接")
            # 使用link的话链接能够点击进行跳转，使用text的话不能点击
            # show_text是指链接显示的文字，但在当前版本Web端大别野会无法正常跳转，最好不使用该参数
        elif arg == "图片":
            msg += MessageSegment.image("https://www.miyoushe.com/_nuxt/img/miHoYo_Game.2457753.png")
            # 暂时只支持url图片，但在当前版本web端无法显示图片，待官方后续修复
    await matcher.finish(msg)
```

使用命令`@bot /发送 艾特我 艾特bot 文字 房间 链接 图片`时，bot会回复`@你的名字 @bot的名字 文字 #房间名 这是链接 图片内容`


## 交流和反馈

目前无论是大别野Bot还是本适配器都在测试开发中，如遇问题请提出issue，感谢支持！

也欢迎来我的大别野【尘世闲游】进行交流：

- 大别野ID: wgiJNaU，可搜索加入
- [Web端链接](https://dby.miyoushe.com/chat/1047/21652)，目前仅PC端可访问

## 相关项目

- [NoneBot2](https://github.com/nonebot/nonebot2): 非常好用的Python跨平台机器人框架！
- [villa-py](https://github.com/CMHopeSunshine/villa-py): 大别野 Bot Python SDK。

推荐有成熟Python开发经验但对NoneBot2不熟悉的小伙伴选择`大别野Bot Python SDK`，

对NoneBot2熟悉或希望接触更成熟的生态的小伙伴选择`NoneBot2+本适配器`进行开发。
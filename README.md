<p align="center">
  <a href="https://v2.nonebot.dev/"><img src="https://v2.nonebot.dev/logo.png" width="200" height="200" alt="nonebot-adapter-villa"></a>
</p>

<div align="center">

# NoneBot-Adapter-Villa

_✨ 大别野 协议适配 ✨_

</div>

## 说明

本适配器仍在开发中。

目前请通过`pip install git+https://github.com/CMHopeSunshine/nonebot-adapter-villa.git@main` 安装。

## 配置

修改 NoneBot 配置文件 `.env` 或者 `.env.*`。

### Driver

本适配器同时需要`ReverseDriver`和`ForwardDriver`，参考 [driver](https://v2.nonebot.dev/docs/next/advanced/driver#%E9%A9%B1%E5%8A%A8%E5%99%A8%E7%B1%BB%E5%9E%8B) 配置项。

如：

```dotenv
DRIVER=~fastapi+~httpx
```

### VILLA_BOTS

配置机器人帐号列表，每个bot有3个必填配置，在大别野机器人开发者社区申请时获得，

- bot_id: 机器人id，以`bot_`开头
- bot_secret: 机器人密钥
- callback_url: http回调地址，例如申请bot时给的回调地址是`http://域名/your/callback/url`，那么配置里的`callback_url`填写`/your/callback/url`
  如：

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

## 使用

### 注册适配器

参考[adapter](https://v2.nonebot.dev/docs/advanced/adapter)注册本适配器，例如：

```python
import nonebot
from nonebot.adapters.villa import Adapter as VillaAdapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(VillaAdapter)

nonebot.load_from_toml("pyproject.toml")
# other...

if __name__ == "__main__":
    nonebot.run()
```

### 编写插件

以下是一个简单的插件示例，展示各种消息段：

```python
from nonebot import on_command
from nonebot.params import CommandArg

from nonebot.adapters.villa import Bot, SendMessageEvent, Message, MessageSegment

matcher = on_command('发送')

@matcher.handle()
async def matcher_handler(bot: Bot, event: SendMessageEvent, arg: Message = CommandArg()):
    if event.room_id != 18509:
        return
    msg = Message()
    lst = arg.extract_plain_text().strip().split(' ')
    for l in lst:
        if l == "艾特我":
            msg += MessageSegment.mention_user(event.from_user_id)
        elif l == "艾特bot":
            msg += MessageSegment.mention_robot()
        elif l == "文字":
            msg += MessageSegment.text("文字")
        elif l == "房间":
            msg += MessageSegment.villa_room_link(event.villa_id, event.room_id)
        elif l == "链接":
            msg += MessageSegment.link("https://www.miyoushe.com/ys/article/39670307")
        elif l == "图片":
            msg += MessageSegment.image("https://upload-bbs.miyoushe.com/upload/2023/05/23/75276539/e49d7d85fc3f6c492e0d26fac3ec7303_6225108250761798626.png?x-oss-process=image//resize,s_600/quality,q_80/auto-orient,0/interlace,1/format,png",
                                        width=690,
                                        height=320,
                                        file_size=436079)
            # 支持url图片，要传图片宽高和字节大小
        else:
            msg += MessageSegment.text(" ")
    await matcher.finish(msg)
```

使用命令`@bot /发送 艾特我 艾特bot 文字 房间 链接 图片`时，bot会回复`@你的名字 @bot的名字 文字 #房间名 https://www.miyoushe.com/ys/article/39670307 图片内容`

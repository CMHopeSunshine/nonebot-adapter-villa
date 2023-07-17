<p align="center">
  <a href="https://v2.nonebot.dev/"><img src="https://v2.nonebot.dev/logo.png" width="200" height="200" alt="nonebot-adapter-villa"></a>
</p>

<div align="center">

# NoneBot-Adapter-Villa

_✨ 大别野 协议适配 ✨_

<a href="https://cdn.jsdelivr.net/gh/CMHopeSunshine/nonebot-adapter-villa@master/LICENSE">
  <img src="https://img.shields.io/github/license/CMHopeSunshine/nonebot-adapter-villa" alt="license">
</a>
<img src="https://img.shields.io/pypi/v/nonebot-adapter-villa" alt="version">
<img src="https://img.shields.io/badge/Python-3.8+-yellow" alt="python">
<a href="https://pypi.python.org/pypi/nonebot-adapter-villa">
  <img src="https://img.shields.io/pypi/dm/nonebot-adapter-villa" alt="pypi download">
</a>
<a href="https://wakatime.com/badge/user/eed3f89c-5d65-46e6-ab19-78dcc4b62b3f/project/838e7f55-f8b8-49ff-aec0-29ad264931cf">
  <img src="https://wakatime.com/badge/user/eed3f89c-5d65-46e6-ab19-78dcc4b62b3f/project/838e7f55-f8b8-49ff-aec0-29ad264931cf.svg" alt="wakatime">
</a>
<a href="https://github.com/astral-sh/ruff">
  <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json" alt="ruff">
</a>

</div>

## 安装

在`nb create`创建项目时选择`Villa`适配器

或在现有`NoneBot2`项目目录下使用脚手架安装：

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

配置 Bot 帐号列表，每个bot有4个必填配置，可前往[「大别野开放平台」](https://open.miyoushe.com/#/login)(ID: `OpenVilla`)申请，取得以下配置：

- `bot_id`: 机器人id，以`bot_`开头
- `bot_secret`: 机器人密钥
- `pub_key`: 加密和验证所需的pub_key
- `callback_url`: http回调地址 endpoint，例如申请bot时给的回调地址是`http://域名/your/callback/url`，那么配置里的`callback_url`填写`/your/callback/url`

此外还有以下选填配置：

- `verify_event`：是否对回调事件签名进行验证

例如：

```dotenv
VILLA_BOTS='
[
  {
    "bot_id": "bot_123456789",
    "bot_secret": "abc123def456",
    "pub_key": "-----BEGIN PUBLIC KEY-----\nyour_pub_key\n-----END PUBLIC KEY-----\n",
    "callback_url": "/your/callback/url",
    "verify_event": true
  }
]
'
```

## 已支持消息段

> 注意，当前大别野只能接收到有@Bot(在哪个位置皆可)的消息事件，且不能有多个@(即使是@两次Bot都不行)

- `MessageSegment.text`: 纯文本
  + 米游社自带表情也是用text来发送，以[表情名]格式，例如MessageSegment.text("[爱心]")
- `MessageSegment.mention_robot`: @机器人
- `MessageSegment.mention_user`: @用户
  + `user_name`和`villa_id`必须给出其中之一，给`villa_id`时，调用api来获取用户名
- `MessageSegment.mention_all`: @全体成员
- `MessageSegment.room_link`: #房间跳转链接
- `MessageSegment.link`: 超链接
  + 使用link的话链接能够点击进行跳转，使用text的话不能点击
  + 字段`show_text`是指链接显示的文字，但若指定了该字段，Web端大别野会无法正常跳转
  + 字段`requires_bot_access_token`为true时，跳转链接会带上含有用户信息的token
- `MessageSegment.quote`: 引用(回复)消息
  + 不能**单独**使用，要与其他消息段一起使用
- `MessageSegment.image`: URL图片
  + 暂时只支持url图片
  + 如果在单次消息中，发送多张图片或者与其他消息段拼接，那么将无法在web端显示出来
- `MessageSegment.post`: 米游社帖子
  + 只能单独发送，与其他消息段拼接时将会被忽略
- `MessageSegment.preview_link`: 预览链接(卡片)
  + 该消息段未在官方文档公开
- `MessageSegment.badge`: 消息徽标
  + 该消息段未在官方文档公开
  + 不能**单独**使用和**单**张图片使用，要与其他消息段一起使用



以下是一个简单的插件示例，展示各种消息段：

```python
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters.villa import MessageSegment, SendMessageEvent, Message

matcher = on_command("test")


@matcher.handle()
async def _(event: SendMessageEvent, args: Message = CommandArg()):
    arg = args.extract_plain_text().strip()
    if arg == "纯文本":
        msg = MessageSegment.text(text="这是一段纯文本")
    elif arg == "艾特bot":
        msg = MessageSegment.mention_robot(
            bot_id=event.robot.template.id, bot_name=event.robot.template.name
        )
    elif arg == "艾特我":
        msg = MessageSegment.mention_user(
            user_id=event.from_user_id, villa_id=event.villa_id
        )
    elif arg == "艾特全体":
        msg = MessageSegment.mention_all()
    elif arg == "房间链接":
        msg = MessageSegment.room_link(villa_id=event.villa_id, room_id=event.room_id)
    elif arg == "超链接":
        msg = MessageSegment.link(
            url="https://www.baidu.com", show_text="百度", requires_bot_access_token=False
        )
    elif arg == "引用消息":
        msg = MessageSegment.quote(event.msg_uid, event.send_at) + MessageSegment.text(
            text="引用原消息"
        )
    elif arg == "图片":
        msg = MessageSegment.image(
            url="https://www.miyoushe.com/_nuxt/img/miHoYo_Game.2457753.png"
        )
    elif arg == "帖子":
        msg = MessageSegment.post(
            post_id="https://www.miyoushe.com/ys/article/40391314"
        )
    elif arg == "预览链接":
        msg = MessageSegment.preview_link(
            icon_url="https://www.bilibili.com/favicon.ico",
            image_url="https://i2.hdslb.com/bfs/archive/21b82856df6b8a2ae759dddac66e2c79d41fe6bc.jpg@672w_378h_1c_!web-home-common-cover.avif",
            is_internal_link=False,
            title="崩坏3第一偶像爱酱",
            content="「海的女儿」——《崩坏3》S级律者角色「死生之律者」宣传PV",
            url="https://www.bilibili.com/video/BV1Mh4y1M79t?spm_id_from=333.1007.tianma.2-2-5.click",
            source_name="哔哩哔哩",
        )
    elif arg == "徽标消息":
        msg = MessageSegment.badge(
            icon_url="https://upload-bbs.mihoyo.com/vila_bot/bbs_origin_badge.png",
            text="徽标",
            url="https://mihoyo.com",
        ) + MessageSegment.text(text="带有徽标的消息")
    else:
        return

    await matcher.finish(msg)

```

使用命令`@bot /test 纯文本`时，bot会回复`这是一段纯文本`


## 交流、建议和反馈

大别野 Bot 和本适配器均为开发测试中，如遇问题请提出 [issue](https://github.com/CMHopeSunshine/nonebot-adapter-villa/issues) ，感谢支持！

也欢迎来我的大别野[「尘世闲游」]((https://dby.miyoushe.com/chat/1047/21652))(ID: `wgiJNaU`)进行交流~

## 相关项目

- [NoneBot2](https://github.com/nonebot/nonebot2): 非常好用的Python跨平台机器人框架！
- [villa-py](https://github.com/CMHopeSunshine/villa-py): 大别野 Bot Python SDK。

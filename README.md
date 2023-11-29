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

配置 Bot 帐号列表，每个 bot 有 3 个必填配置，可前往[「大别野开放平台」](https://open.miyoushe.com/#/login)申请，取得以下配置：

- `bot_id`: 机器人id，以`bot_`开头
- `bot_secret`: 机器人密钥
- `pub_key`: 加密和验证所需的 pub_key (请使用开放平台中的复制按钮而不是手动复制)

此外，还要根据连接方式填写额外配置：

- `connection_type`: 连接方式，填写 `webhook` 或 `websocket`，默认为 `webhook`

### Webhook 连接

- `callback_url`: http 回调地址 endpoint，例如开放平台中回调地址是`http://域名/your/callback/url`，那么配置里的 `callback_url` 填写 `/your/callback/url`
- `verify_event`：是否对回调事件签名进行验证，默认为 `True`

使用 webhook 方式连接时，驱动器需要 `ReverseDriver` 和 `ForwardDriver`，参考 [driver](https://v2.nonebot.dev/docs/next/advanced/driver#%E9%A9%B1%E5%8A%A8%E5%99%A8%E7%B1%BB%E5%9E%8B) 配置项。

webhook 配置完整示例：

```dotenv
DRIVER=~fastapi+~httpx
VILLA_BOTS='
[
  {
    "bot_id": "bot_123456789",
    "bot_secret": "abc123def456",
    "pub_key": "-----BEGIN PUBLIC KEY-----\nyour_pub_key\n-----END PUBLIC KEY-----\n",
    "connection_type": "webhook",
    "callback_url": "/your/callback/url",
    "verify_event": true
  }
]
'
```

### Websocket 连接 (官方测试中)

- `test_villa_id`: 未上线时填写调试别野的id，已上传公域 bot 填写 `0`

使用 websocket 方式连接时，驱动器需要 `ForwardDriver`，参考 [driver](https://v2.nonebot.dev/docs/next/advanced/driver#%E9%A9%B1%E5%8A%A8%E5%99%A8%E7%B1%BB%E5%9E%8B) 配置项。

websocket 配置完整示例：

```dotenv
DRIVER=~httpx+~websocket
VILLA_BOTS='
[
  {
    "bot_id": "bot_123456789",
    "bot_secret": "abc123def456",
    "pub_key": "-----BEGIN PUBLIC KEY-----\nyour_pub_key\n-----END PUBLIC KEY-----\n",
    "connection_type": "websocket",
    "test_villa_id": 0
  }
]
'
```

## 已支持消息段

- `MessageSegment.text`: 纯文本
  + 米游社自带表情也是用text来发送，以[表情名]格式，例如：MessageSegment.text("[爱心]")
  + 支持样式:
    + `bold`: 加粗
    + `italic`: 斜体
    + `underline`: 下划线
    + `strikethrough`: 删除线
  + 例如：MessageSegment.text("加粗", blod=True) + MessageSegment.text("斜体", italic=True)
- `MessageSegment.mention_robot`: @机器人
- `MessageSegment.mention_user`: @用户
  + `user_name` 和 `villa_id` 必须给出其中之一，给 `villa_id` 时，调用 api 来获取用户名
- `MessageSegment.mention_all`: @全体成员
- `MessageSegment.room_link`: #房间跳转链接
- `MessageSegment.link`: 超链接
  + 使用link的话链接能够点击进行跳转，使用text的话不能点击
  + 字段 `show_text` 是指链接显示的文字，但若指定了该字段，Web端大别野会无法正常跳转
  + 字段 `requires_bot_access_token` 为true时，跳转链接会带上含有用户信息的token
- `MessageSegment.quote`: 引用(回复)消息
  + 不能**单独**使用，要与其他消息段一起使用
- `MessageSegment.image`: URL 图片
  + 图片 url 需为米哈游官方图床 url
  + 非官方图床 url 可以通过 `Bot.transfer_image` 接口转换为官方图床 url
  + 本地图片可以通过 `Bot.upload_image` 接口来上传图片，使用返回结果的 url 来发送
  + 多张图片拼接时，只会发送最后一张图片
  + 与其他消息段拼接时，将无法在 web 端显示出来
- `MessageSegment.post`: 米游社帖子
  + 只能单独发送，与其他消息段拼接时将会被忽略
- `MessageSegment.preview_link`: 预览链接(卡片)
  + 该消息段未在官方文档公开
  + 无法在 web 端显示出来
- `MessageSegment.badge`: 消息徽标(消息下方的可链接跳转的下标)
  + 该消息段未在官方文档公开
  + 不能**单独**使用，要与其他消息段一起使用
  + 无法在 web 端显示出来
- 消息组件，有两种构造方式：
  + `MessageSegment.components`：传入若干个component，适配器会自动根据组件显示的文本长度来计算组件面板布局(推荐)
  + `MessageSegment.panel`：传入一个组件模板 ID 或自己构造好的自定义组件面板布局 `Panel` 对象



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


关于消息组件的详细介绍：

```python
from nonebot.adapters.villa.message import MessageSegment
from nonebot.adapters.villa.models import CallbackButton, InputButton, LinkButton, Panel

# 目前有三种按钮组件，每个组件都必须有 id 和 text 字段
# id字段用于标识组件，必须是唯一的，text字段用于显示组件的文本
# need_callback字段如果设为True，表示点击按钮后会触发ClickMsgComponentEvent事件回调
# extra字段用于开发者自定义，可以在事件回调中获取到

# 文本按钮
# 用户点击后，会将按钮的 input 字段内容填充到用户的输入框中
input_button = InputButton(
    id="1",
    text="文本按钮",
    input="/文本",
)

# 回调按钮
# need_callback恒为True，点击按钮后会触发ClickMsgComponentEvent事件回调
callback_button = CallbackButton(
    id="2",
    text="回调按钮",
)

# 链接按钮
# 用户点击后，会跳转到按钮的 link 字段所指定的链接
# need_token字段为True时，会在链接中附带token参数，用于验证用户身份
link_button = LinkButton(
    id="3",
    text="链接按钮",
    link="https://www.baidu.com",
    need_token=True,
)

# 构造消息段
com_msg = MessageSegment.components(
    input_button,
    callback_button,
    link_button,
)

# 适配器会自动根据每个组件的text字段的长度，自动调整按钮的排版
# 如果需要自定义排版，可以使用MessageSegment.panel方法
# 自己构造好Panel对象，传入
panel = Panel(mid_component_group_list=[[input_button, callback_button], [link_button]])
com_msg = MessageSegment.panel(panel)

# 如果有预先设置好的消息组件模板 ID，可以直接使用
template_id = 123456
com_msg = MessageSegment.panel(template_id)

# 如果有多个 MessageSegment.panel 相加，则只会发送最后一个
```


## 交流、建议和反馈

大别野 Bot 和本适配器均为开发测试中，如遇问题请提出 [issue](https://github.com/CMHopeSunshine/nonebot-adapter-villa/issues) ，感谢支持！

也欢迎来开发者的大别野[「尘世闲游」]((https://dby.miyoushe.com/chat/1047/21652))(ID: `wgiJNaU`)进行交流~

## 相关项目

- [NoneBot2](https://github.com/nonebot/nonebot2): 非常好用的 Python 跨平台机器人框架！
- [villa-py](https://github.com/CMHopeSunshine/villa-py): 大别野 Bot Python SDK。

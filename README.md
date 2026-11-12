 HEAD
# ITest 脚本

## 下载安装

git拉取, 也可以直接下载源码

```bash
git clone https://github.com/YDHusky/itest.git
```

## 配置

安装依赖

```bash
pip install -r requirements.txt
```

修改config.yml中 相关账户密码及配置部分启动即可
```yaml
username: "" # 用户名
password: "" # 密码
ai:
  base_url: "https://api.deepseek.com/v1"
  model: "deepseek-chat"
  apikey: "" # https://platform.deepseek.com/usage(默认deepseek)
driver_type: "edge" # 支持firefox,chrome,edge[默认edge]
sleep_time: 10 # 单位: s
```

## 启动
```bash
python main.py
```
启动发现需要完成的考试输入y即可, 部分考试需要考试码!
=======
# itest-
本脚本根据@YDHusky公开版本进行修改和优化，并借助Gemini增添了正式考试功能，解决了正式考试会跳转新页面的问题，可自动完成听力
>>>>>>> 341996a5c7ed8a5dc0494cb8e66ebb2da19d249c

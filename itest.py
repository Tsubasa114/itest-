import json
import os
import shutil
import time
from urllib.parse import urlparse, parse_qs

from husky_spider_utils import SeleniumSession
from selenium.webdriver.common.by import By

from kimi_model import ItestKimi
from mp32str import mp3_to_wav, wav_to_str
from loguru import logger


class ITest:
    base_url = "https://sso.unipus.cn/sso/login?service=https%3A%2F%2Fitestcloud.unipus.cn%2Futest%2Fitest%2Flogin%3F_rp%3D%252Fitest%253Fx%253D1742213323268"

    def __init__(self, username, password, api_key, model="deepseek-chat", base_url="https://api.deepseek.com/v1",
                 driver_type="edge"):
        self.session = SeleniumSession(self.base_url, driver_type=driver_type)
        self.ai_client = ItestKimi(api_key=api_key, model=model, base_url=base_url)
        self.login(username, password)

    def login(self, username, password):
        # 保留基础自动填写逻辑作为初始尝试，如遇验证码或拦截可直接在浏览器手动操作
        try:
            self.session.send_key("input[name='username']", username)
            self.session.send_key("input[name='password']", password)
            self.session.click(".help-block input[type='checkbox']")
            self.session.click("#login")
        except Exception:
            pass

    def get_exams(self):
        self.session.selenium_get("https://itestcloud.unipus.cn/utest/itest/s/exam")
        exams_list = []

        def get_res(page: int):
            payload = {
                "curPage": page,
                "pageSize": 5
            }
            res = self.session.post("https://itestcloud.unipus.cn/utest/itest-mobile-api/student/exam/list",
                                    json=payload)
            if res.json()['msg'] == "SUCCESS":
                return res.json()['rs']['totalPage'], res.json()['rs']['data']
            else:
                return None

        total_page, data = get_res(1)
        exams_list.extend(data)
        if total_page > 1:
            for i in range(2, total_page + 1):
                _, data = get_res(page=i)
                exams_list.extend(data)
        return exams_list

    def get_mock(self):
        self.session.selenium_get(
            "https://itestcloud.unipus.cn/utest/itest/s/train"
        )

        input("请检查 Edge 浏览器中的登录页面，完成允许的手动登录后，按回车继续……")

        self.session.selenium_get("https://itestcloud.unipus.cn/utest/itest/s/jcxl/mock")

        from parsel import Selector
        html = Selector(text=self.session.driver.page_source)
        title = html.css("title::text").get()
        mock_table = html.css(".paper-table tbody tr")
        mock_data = []

        for tr in mock_table:
            tds = tr.css("td")
            if len(tds) >= 5:
                mock_data.append({
                    "id": tds[0].css("::text").get(),
                    "mock_id": tds[1].css("::text").get(),
                    "name": tds[2].css("::text").get(),
                    "times": tds[3].css("::text").get(),
                    "score": tds[4].css("::text").get(),
                })

        if not mock_data:
            logger.error("没有匹配到模拟练习列表，以下是调试信息：")
            logger.error(f"当前页面网址：{getattr(self.session, 'get_current_url', lambda: '未知')()}")
            logger.error(f"网页标题：{title!r}")
            preview = self.session.driver.page_source[:1500].replace("\r", " ").replace("\n", " ")
            logger.error(f"网页内容预览（前 1500 字符，请检查并遮盖敏感信息后再分享）：{preview}")

        logger.info(f"匹配到的模拟练习数量：{len(mock_data)}")
        return mock_data

    def to_mock_exam(self, mock_info):
        mock_id = mock_info['mock_id']
        url = f"https://itestcloud.unipus.cn/utest/itest/s/jcxl/mock/doMockTest?ppId={mock_id}&returnUrl=https://itestcloud.unipus.cn/utest/itest/s/jcxl/mock"
        self.session.selenium_get(url)
        current_url = self.session.get_current_url()
        parsed_url = urlparse(current_url)
        params = parse_qs(parsed_url.query)
        token = params.get('token', [None])[0]
        self.session.try_click(".layui-layer-btn0", max_attempt=1, timeout=5)
        self.common_to_exam(token=token, return_url='https://itestcloud.unipus.cn/utest/itest/s/jcxl/mock&skipEnvTest=true')

    def common_to_exam(self, token:str, return_url:str):
        payload = {
            "token": token
        }
        data = {}
        self.session.headers.update(payload)
        res = self.session.post("https://itestcloud.unipus.cn/utest/itest-mobile-api/student/exam/examToken", data=data)
        url = res.json()["rs"]["url"] + f"&returnUrl={return_url}"
        self.session.selenium_get(url)
        self.session.try_click(".layui-layer-btn0", max_attempt=1, timeout=3)
        self.session.try_click("#success-ok", max_attempt=1, timeout=3)

    def to_exam(self, exam_info):
        ksd_id = exam_info['ksdId']
        payload = {
            "examId": ksd_id,
            "examCode": ""
        }
        if exam_info['examCodeFlag']:
            payload['examCode'] = input("请输入六位考试码:")
            
        try:
            res = self.session.post("https://itestcloud.unipus.cn/utest/itest/s/clsanswer/judgeEntry", data=payload)
            res_json = res.json()
            
            if "data" in res_json and res_json["data"]:
                url = res_json["data"]["url"]
                token = res_json["data"]["token"]
                url = url + "&returnUrl=https://itestcloud.unipus.cn/utest/itest/s/exam"
                self.session.selenium_get(url)
                self.session.try_click(".layui-layer-btn0", max_attempt=1, timeout=5)
                self.common_to_exam(token, 'https://itestcloud.unipus.cn/utest/itest/s/exam&skipEnvTest=true')
                return
        except Exception as e:
            logger.warning(f"自动请求正式考试入口遇到异常: {e}")

        logger.warning("无法通过后端接口直接进入正式考试。")
        input("请在 Edge 浏览器中【手动点击进入】该正式考试答题页面（跳转后的新界面）。进入后按回车，脚本将直接开始作答……")

    def switch_to_latest_window(self):
        """自动切换到浏览器最新打开的标签页或窗口（解决跳转新界面抓不到元素的问题）"""
        try:
            windows = self.session.driver.window_handles
            if len(windows) > 1:
                self.session.driver.switch_to.window(windows[-1])
                logger.info("已自动切换到跳转后的最新考试标签页。")
        except Exception as e:
            logger.warning(f"切换窗口时发生异常: {e}")

    def download_mp3(self):
        # 确保操作的是最新跳转的考试界面
        self.switch_to_latest_window()
        
        logger.info("正在等待并获取试卷听力与题目内容区域...")
        max_wait = 30
        start_time = time.time()
        sections = None
        
        while time.time() - start_time < max_wait:
            try:
                sections = self.session.get_element_selector("#main-content .itest-section")
                if sections:
                    break
            except Exception:
                pass
            time.sleep(2)
            
        if not sections:
            logger.error("未能在页面中找到 #main-content .itest-section 元素。请确认当前是否在正式考试答题页面。")
            raise TimeoutException("加载题目区域超时")

        all_hear = sections.css(".itest-hear-reslist::text").getall()
        hear_list = []
        if os.path.exists("hear_temp"):
            shutil.rmtree("hear_temp")
        os.mkdir("hear_temp")
        for item in all_hear:
            hear_list.extend(json.loads(item))
        for i, hear in enumerate(hear_list):  # type: int, str

            if hear.startswith("http"):
                res = self.session.get(hear, is_refresh=False)
                with open(f"./hear_temp/hear{i}.mp3", "wb") as f:
                    f.write(res.content)

    def mp3_to_str(self):
        mp3_to_wav()
        mp3_str = wav_to_str()
        return mp3_str

    def ai_get_ans(self):
        logger.info("下载听力资源中...")
        self.download_mp3()
        logger.info("转换听力资源中...")
        mp3_str = self.mp3_to_str()
        logger.success(f"听力文本: {mp3_str}")
        
        # 确保在最新跳转的考试界面获取源码
        self.switch_to_latest_window()
        page_source = self.session.get_element_selector("#main-content .itest-section").getall()
        page_source_data = "".join(page_source)
        logger.info("ai生成答案中...")
        ans_data = self.ai_client.write(page_source_data, mp3_str)['ans']
        logger.info("ai生成完成！")
        return ans_data

    def write_ans(self, ans: list):
        self.switch_to_latest_window()
        logger.info("即将为您按进度平稳填写答案!")
        for i, ans_data in enumerate(ans):
            qid = ans_data['qid']
            q_type = ans_data['type']
            css = ans_data['css']
            a = ans_data['ans']
            logger.success(f"正在完成题目 {qid}: {a}")
            
            if q_type == "write":
                self.session.send_key(css, a)
                if i != len(ans) - 1:
                    self.next_page()
            elif q_type == "select":
                self.session.try_click(css, max_attempt=1, timeout=5)
                if i != len(ans) - 1:
                    next_ans = ans[i + 1]
                    if next_ans['type'] != "write":
                        if next_ans['qsubindex'] == "1":
                            self.next_page()
                    else:
                        self.next_page()
            elif q_type == "input":
                self.session.send_key(css, a)
                if i != len(ans) - 1:
                    next_ans = ans[i + 1]
                    if next_ans['type'] != "write":
                        if next_ans['qsubindex'] == "1":
                            self.next_page()
                    else:
                        self.next_page()
            
            time.sleep(0.6)

    def submit(self, sleep_time=3):
        self.switch_to_latest_window()
        time.sleep(sleep_time)
        self.session.try_click("#submit-answer", max_attempt=1, timeout=3)
        self.session.try_click(".layui-layer-btn0", max_attempt=1, timeout=3)
        time.sleep(5)

    def next_page(self):
        self.session.try_click("#footer .goto a", max_attempt=1, timeout=3)
import time

import yaml
from loguru import logger

from itest import ITest

config = yaml.load(open("config.yml", "r", encoding="utf-8"), Loader=yaml.FullLoader)

if __name__ == '__main__':
    itest = ITest(
        username=config['username'], 
        password=config['password'], 
        model=config['ai']['model'],
        driver_type=config['driver_type'], 
        api_key=config['ai']['apikey'], 
        base_url=config['ai']['base_url']
    )
    
    # 引导用户选择操作类型
    print("=" * 40)
    print("请选择要操作的功能：")
    print("[1] 模拟练习 (支持自选题目)")
    print("[2] 正式考试 (https://itestcloud.unipus.cn/utest/itest/s/exam)")
    print("=" * 40)
    mode_choice = input("请输入编号 (默认 1): ").strip()

    if mode_choice == "2":
        # --- 正式考试分支 ---
        logger.info("正在获取正式考试列表...")
        data = itest.get_exams()
        
        if not data:
            logger.error("没有获取到正式考试列表。请确认已成功登录 iTest 且当前有可用的正式考试。")
            raise SystemExit(1)

        logger.info(f"获取到 {len(data)} 个正式考试项目：")
        for i, item in enumerate(data):
            exam_name = item.get('examName') or item.get('name') or '未命名考试'
            start_time = item.get('startTime', '未知')
            print(f"[{i}] 名称: {exam_name} | 开始时间: {start_time}")

        try:
            choice = input(f"请输入你想选择的正式考试编号 (0 ~ {len(data) - 1}，默认第一个): ").strip()
            if choice == "":
                selected_index = 0
            else:
                selected_index = int(choice)
                if selected_index < 0 or selected_index >= len(data):
                    print("输入超出范围，将自动为您选择第一个！")
                    selected_index = 0
        except ValueError:
            print("输入无效，将自动为您选择第一个！")
            selected_index = 0

        chosen_exam = data[selected_index]
        exam_name = chosen_exam.get('examName') or chosen_exam.get('name') or '未命名考试'
        logger.info(f"你选择了正式考试: {exam_name}")

        # 跳转并作答正式考试
        itest.to_exam(chosen_exam)
        itest.write_ans(itest.ai_get_ans())

    else:
        # --- 模拟练习分支 (默认) ---
        data = itest.get_mock()

        if not data:
            logger.error(
                "没有获取到模拟考试列表。请确认已成功登录 iTest、账号有权访问模拟练习，"
                "并检查网页结构或网络请求是否发生变化。"
            )
            raise SystemExit(1)

        logger.info(f"获取到 {len(data)} 个模拟练习项目：")
        
        for i, item in enumerate(data):
            print(f"[{i}] 名称: {item.get('name')} | 次数: {item.get('times')} | 分数: {item.get('score')}")

        try:
            choice = input(f"请输入你想选择的模拟练习编号 (0 ~ {len(data) - 1}，默认最后一个): ").strip()
            if choice == "":
                selected_index = -1  # 默认选最后一个
            else:
                selected_index = int(choice)
                if selected_index < 0 or selected_index >= len(data):
                    print("输入超出范围，将自动为您选择最后一个！")
                    selected_index = -1
        except ValueError:
            print("输入无效，将自动为您选择最后一个！")
            selected_index = -1

        chosen_mock = data[selected_index]
        logger.info(f"你选择了模拟练习: {chosen_mock.get('name')}")

        # 跳转并作答模拟练习
        itest.to_mock_exam(chosen_mock)
        itest.write_ans(itest.ai_get_ans())

    # --- 统一的收尾与手动提交提示 ---
    logger.success("答案已全部填写完毕！")
    input("请在浏览器中检查答案，手动点击提交试卷。确认无误后，在此处按回车键退出程序...")
import mujoco.viewer
import time
import sys
import json


def run_simulation(ctrl_params):
    model = mujoco.MjModel.from_xml_path('model/universal_robots_ur5e/scene.xml')
    data = mujoco.MjData(model)

    # 应用控制参数
    if len(ctrl_params) >= 6:
        data.ctrl[:6] = ctrl_params[:6]
    else:
        print(f"警告: 不足的控制参数数量，使用默认值")
        data.ctrl[:6] = [0, 0, 0, 0, 0, 0]

    with mujoco.viewer.launch_passive(model, data) as viewer:
        print("仿真已启动，控制参数:", data.ctrl[:6])

        try:
            while viewer.is_running():
                mujoco.mj_step(model, data)

                # 更新可视化
                viewer.sync()

                # 检查是否有新的控制参数文件
                try:
                    with open("ctrl_params.json", "r") as f:
                        new_params = json.load(f)
                    if new_params and len(new_params) >= 6:
                        data.ctrl[:6] = new_params[:6]
                        print("更新控制参数:", data.ctrl[:6])
                except FileNotFoundError:
                    # 文件可能被暂时删除或移动
                    pass
                except json.JSONDecodeError:
                    print("警告: 无法解析控制参数文件")

                time.sleep(0.0001)  # 控制更新频率
        except Exception as e:
            print(f"仿真错误: {str(e)}")


if __name__ == "__main__":
    # 尝试从JSON文件加载参数
    try:
        with open("ctrl_params.json", "r") as f:
            ctrl_params = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        ctrl_params = None

    # 如果文件读取失败，使用默认值
    if not ctrl_params or len(ctrl_params) < 6:
        ctrl_params = [0, -1, -1, 0, 0, 0]
        print("使用默认控制参数")

    run_simulation(ctrl_params)
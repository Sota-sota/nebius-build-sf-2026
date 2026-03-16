import sys
import os

# フォルダが二重になっている可能性が高いので、一つ深く設定します
LEROBOT_PATH = "/home/saito/git-files/nebius.rerobot/lerobot/lerobot"
ROOT_PATH = "/home/saito/git-files/nebius.rerobot/lerobot" # 親フォルダも追加

sys.path.append(ROOT_PATH)
sys.path.append(LEROBOT_PATH)

print(f"FORCED PATH: {LEROBOT_PATH}")

try:
    # これで lerobot.common が見えるはずです
    import lerobot
    from lerobot.common.robot_devices.robots.factory import make_robot
    print("SUCCESS: lerobot imported!")
except ImportError as e:
    # もしこれでもダメな場合、lsコマンドで中身を確認してください
    print(f"FAILED: {e}")
    os.system(f"ls -F {LEROBOT_PATH}")

import time
import json
import torch
from lerobot.common.robot_devices.robots.factory import make_robot
from config import ARM_PORT, ARM_ID

robot = make_robot("so101_follower", port=ARM_PORT, id=ARM_ID)
robot.connect()
recorded_data = []
print("Recording started... Move the arm! (Press Ctrl+C to stop)")

try:
    while True:
        state = robot.read_state() # 角度を取得
        recorded_data.append(state.tolist())
        time.sleep(0.05) # 20fpsで記録
except KeyboardInterrupt:
    with open("picked_motion.json", "w") as f:
        json.dump(recorded_data, f)
    print(f"\nSaved {len(recorded_data)} frames to picked_motion.json")
"""
SO101 アーム校正スクリプト
実行すると各位置でアームを手動で動かしてジョイント角度を記録できる。
記録した値を config.py の POSITION_MAP に貼り付けること。
"""

import sys
sys.path.insert(0, "../backend")

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]


def main():
    print("=" * 50)
    print("SO101 Arm Calibration")
    print("=" * 50)

    try:
        from lerobot.robots import make_robot_from_config
        from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
        from config import ARM_PORT, ARM_ID

        print(f"\nConnecting to arm at {ARM_PORT}...")
        config = SOFollowerRobotConfig(port=ARM_PORT, id=ARM_ID, disable_torque_on_disconnect=True)
        robot = make_robot_from_config(config)
        robot.connect(calibrate=False)
        print("Connected!")
    except Exception as e:
        print(f"[ERROR] Could not connect to arm: {e}")
        print("Check USB connection and ARM_PORT in .env")
        return

    positions = {}
    targets = ["home", "far-left", "center-left", "center", "center-right", "far-right", "above"]

    print("\nCalibration procedure:")
    print("1. Move arm to each position manually (torque-off mode)")
    print("2. Press Enter to record joint angles")
    print("3. Results will be printed as POSITION_MAP for config.py\n")

    for target in targets:
        input(f"Move arm to '{target}' position, then press Enter...")
        try:
            obs = robot.get_observation()
            joints = [obs.get(f"{name}.pos", 0.0) for name in MOTOR_NAMES]
            positions[target] = [round(v, 3) for v in joints]
            print(f"  Recorded {target}: {positions[target]}\n")
        except Exception as e:
            print(f"  [ERROR] Could not read joints: {e}")
            manual = input(f"  Enter 6 joint values manually (comma-separated): ")
            positions[target] = [float(v.strip()) for v in manual.split(",")]

    robot.disconnect()

    print("\n" + "=" * 50)
    print("Copy this into backend/config.py → POSITION_MAP:")
    print("=" * 50)
    print("\nPOSITION_MAP = {")
    for name, vals in positions.items():
        print(f'    "{name}": {vals},')
    print("}")
    print()


if __name__ == "__main__":
    main()

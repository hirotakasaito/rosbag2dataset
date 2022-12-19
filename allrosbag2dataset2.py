#!/usr/bin/python3

import os
import argparse
import json
import subprocess
from glob import iglob


def main():

    print("\n" + "==== Config Creater ====" + "\n")

    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--rosbag-dir", type=str, default="/share/private/27th/hirotaka_saito/bagfile/sq2/d_kan1/syuukai")
    parser.add_argument("-o", "--output-dir", type=str, default="/share/private/27th/hirotaka_saito/dataset/sq2/d_kan1/test_4hz")
    parser.add_argument("-c", "--config-dir", type=str, default="/share/private/27th/hirotaka_saito/config2/")
    args = parser.parse_args()

    config = {}
    config["topics"] = ["camera/color/image_raw/compressed","front_laser/scan","t_frog/cmd_vel","t_frog/odom"]
    config["dataset"] = ["acs" ,"lidar", "pos","obs"]
    config["hz"] = 2.5
    config["traj_steps"] = 5
    config["goal_steps"] = 500
    config["output_dir"] = args.output_dir
    config["bagfile_dir"] = args.rosbag_dir
    config["action_noise"] = 0.0
    config["lower_bound"] = [0.0, -1.5]
    config["upper_bound"] = [1.5, 1.5]
    config["collision_upper_bound"] = 1.3
    config["collision_lower_bound"] = 0.3
    config["width"] = 224
    config["height"] = 224
    config["midas_type"] = "MiDaS_small"
    config["use_midas"] = False

    count = 1
    rosbag_names = []
    for bag_path in iglob(os.path.join(args.rosbag_dir, "*")):
        _,expand = os.path.splitext(bag_path)
        if expand == ".bag":
            rosbag_names.append(os.path.basename(bag_path))

        if len(rosbag_names) == 0:
            continue

    for rosbag_name in rosbag_names:
        config["bagfile_name"] = [f"{rosbag_name}"]
        print(rosbag_name)

        os.makedirs(args.config_dir, exist_ok=True)
        with open(os.path.join(args.config_dir, f"config{count}.json"), "w") as f:
            json.dump(config, f, indent=4)

        count += 1

    print("\n" + "==== Created Config ====" + "\n")

    for config_path in iglob(os.path.join(args.config_dir,"*")):
        config_name = os.path.basename(config_path)
        print(config_name)
        command = "python3 ./rosbag2dataset.py --config /share/private/27th/hirotaka_saito/config2/" + config_name

        proc = subprocess.run(command,shell=True,stdout=subprocess.PIPE,text=True)
        print(proc.check_returncode())
        print(proc.stdout)



if __name__ == "__main__":
    main()

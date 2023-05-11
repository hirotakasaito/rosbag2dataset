#!/usr/bin/python3

import os
import argparse
import json
import subprocess
from glob import iglob
from multiprocessing import Pool
import shutil


def each_convert2torch(config_name):
    command = "python3 ./rosbag2dataset.py --config /share/private/27th/hirotaka_saito/config/" + config_name
    proc = subprocess.run(command,shell=True,stdout=subprocess.PIPE,text=True)

def main():

    print("\n" + "==== Config Creater ====" + "\n")

    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--rosbag-dir", type=str, default="/share/private/27th/hirotaka_saito/bagfile/sq2/d_kan1/test/")
    parser.add_argument("-o", "--output-dir", type=str, default="/share/private/27th/hirotaka_saito/dataset/sq2/d_kan1/test_midas_point/")
    parser.add_argument("-c", "--config-dir", type=str, default="/share/private/27th/hirotaka_saito/config/")
    parser.add_argument('--num-core', type=int, default=1)
    args = parser.parse_args()

    config = {}
    config["topics"] = ["camera/color/image_raw/compressed", "front_laser/scan", "t_frog/odom"]
    # config["dataset"] = ["acs" ,"lidar" ,"pos" ,"obs3", "obs3d", "goal", "goal_obs"]
    # config["dataset"] = ["acs" ,"goal" ,"obs","goal_obs"]
    # config["topics"] = ["camera/color/image_raw/compressed","front_laser/scan","t_frog/cmd_vel","t_frog/odom","imu/data"]
    config["dataset"] = ["acs" ,"lidar", "pos","obs", "midas_point"]
    config["hz"] = 5
    config["traj_steps"] = 15
    config["goal_steps"] = 0
    config["output_dir"] = args.output_dir
    config["bagfile_dir"] = args.rosbag_dir
    config["action_noise"] = 0.0
    config["lower_bound"] = [0.0, -1.5]
    config["upper_bound"] = [1.5, 1.5]
    config["collision_upper_bound"] = 1.3
    config["collision_lower_bound"] = 0.3
    config["width"] = 224
    config["height"] = 224
    # config["midas_type"] = "MiDaS_small"
    config["midas_type"] = "DPT_Large"
    config["use_midas"] = False
    config["use_midas_point"] = True
    config["divide_count"] = 1

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
    os.makedirs(args.config_dir, exist_ok=True)

    if args.num_core == 1:
        for config_path in iglob(os.path.join(args.config_dir,"*")):
            config_name = os.path.basename(config_path)
            print(config_name)
            command = "python3 ./rosbag2dataset.py --config /share/private/27th/hirotaka_saito/config/" + config_name

            proc = subprocess.run(command,shell=True,stdout=subprocess.PIPE,text=True)
            print(proc.check_returncode())
            print(proc.stdout)
    else:
        config_names = []
        for config_path in iglob(os.path.join(args.config_dir,"*")):
            config_name = os.path.basename(config_path)
            config_names.append(config_name)

        with Pool(args.num_core) as p:
            p.map(each_convert2torch, config_names)

    shutil.rmtree(args.config_dir)

if __name__ == "__main__":
    main()

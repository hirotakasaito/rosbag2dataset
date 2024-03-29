#!/usr/bin/env python3
import os
import argparse
import json
from tqdm import tqdm

import torch

from rosbaghandler import RosbagHandler
from utils import *

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default="config.json")
    args = parser.parse_args()

    if os.path.exists(args.config):
        with open(args.config, "r") as f:
            config = json.load(f)
    else:
        raise ValueError("cannot find config file")

    model_type = config["midas_type"]
    use_midas = config["use_midas"]
    use_midas_point = config["use_midas_point"]
    divide_count = config["divide_count"]
    hz = config["hz"]
    divide_time = 1.0 / hz /divide_count

    if use_midas or use_midas_point:
        midas = torch.hub.load("intel-isl/MiDaS", model_type)
        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        midas.to(device)
        midas.eval()

        if model_type == "DPT_Large" or model_type == "DPT_Hybrid":
            transform = midas_transforms.dpt_transform
        else:
            transform = midas_transforms.small_transform

    for bagfile_name in config["bagfile_name"]:
        bagfile = os.path.join(config["bagfile_dir"], bagfile_name)
        if not os.path.exists(bagfile):
            raise ValueError('set bagfile')
        file_name = os.path.splitext(os.path.basename(bagfile))[0]+"_traj"+str(config["traj_steps"])
        out_dir = os.path.join(config["output_dir"], file_name)
        print("out_dir: ", out_dir)
        os.makedirs(out_dir, exist_ok=True)
        for data_name in config["dataset"]:
            os.makedirs(os.path.join(out_dir, data_name), exist_ok=True)
        rosbag_handler = RosbagHandler(bagfile)

        file_count = 0
        for each_divide_count in range(divide_count):
            t0 = rosbag_handler.start_time + each_divide_count * divide_time
            t1 = rosbag_handler.end_time
            sample_data = rosbag_handler.read_messages(topics=config["topics"], start_time=t0, end_time=t1, hz=config["hz"])
            dataset = {}
            for topic in sample_data.keys():
                topic_type = rosbag_handler.get_topic_type(topic)
                print(topic_type)
                if topic_type == "sensor_msgs/CompressedImage":
                    print("==== convert compressed image ====")
                    if topic == "camera/color/image_raw/compressed":
                        dataset["obs"] = convert_CompressedImage(sample_data[topic], config["height"], config["width"])
                        if use_midas:
                            dataset["obsd"] = convert_CompressedImage_depth(dataset["obs"], midas, device, transform, config["height"], config["width"])
                        if use_midas_point:
                            dataset["midas_point"] = convert_CompressedImage_depth2point(dataset["obs"], midas, device, transform, config["height"], config["width"])

                    if topic == "front_right_camera/color/image_raw/compressed":
                        dataset["obsright"] = convert_CompressedImage(sample_data[topic], config["height"], config["width"])

                        if use_midas:
                            dataset["obsrightd"] = convert_CompressedImage_depth(dataset["obsright"], midas, device, transform, config["height"], config["width"])

                    if topic == "front_left_camera/color/image_raw/compressed":
                        dataset["obsleft"] = convert_CompressedImage(sample_data[topic], config["height"], config["width"])

                        if use_midas:
                            dataset["obsleftd"] = convert_CompressedImage_depth(dataset["obsleft"], midas , device, transform, config["height"], config["width"])

                elif topic_type == "":
                    print("==== convert image ====")
                    dataset["obs"] = convert_Image(sample_data[topic], config["height"], config["width"])
                elif topic_type == "nav_msgs/Odometry":
                    print("==== convert odometry ====")
                    dataset['acs'], dataset['pos'] = \
                        convert_Odometry(sample_data[topic], config['action_noise'],
                                            config['lower_bound'], config["upper_bound"])
                elif topic_type == "geometry_msgs/Twist":
                    print("==== convert cmd_vel ====")
                    dataset['acs'], dataset['pos'] = convert_Twist(sample_data[topic], config['action_noise'], config['lower_bound'], config["upper_bound"], hz=config["hz"], use_pose=True)
                elif topic_type == "sensor_msgs/LaserScan":
                    print("==== convert laser scan ====")
                    dataset["lidar"] = convert_LaserScan(sample_data[topic])
                elif topic_type == "sensor_msgs/Imu":
                    print("==== convert imu ====")
                    dataset["imu"] = convert_Imu(sample_data[topic])
                elif topic_type == "geometry_msgs/PoseWithCovarianceStamped":
                    print("==== convert pose ====")
                    dataset["global_pos"] = convert_PoseWithCovarianceStamped(sample_data[topic])

            print("==== save data as torch tensor ====")
            if "goal" in config["dataset"]:
                num_steps = len(dataset["acs"]) - config["goal_steps"]
            else:
                num_steps = len(dataset["obs"])
            num_traj = int(num_steps/config["traj_steps"])

            use_obs3_img_flag = False
            use_obs3d_img_flag = False

            for data_name in config["dataset"]:
                if data_name == "obs3":
                    use_obs3_img_flag = True
                    concat_imgs = []
                    for obs_front, obs_right, obs_left in zip(dataset["obs"], dataset["obsright"], dataset["obsleft"]):
                        concat_img = cv2.hconcat([obs_left, obs_front, obs_right])
                        concat_imgs.append(concat_img)
                    dataset["obs3"] = concat_imgs

                if data_name == "obs3d":
                    use_obs3d_img_flag = True
                    concat_imgs = []
                    for obs_front, obs_right, obs_left in zip(dataset["obsd"], dataset["obsrightd"], dataset["obsleftd"]):
                        concat_img = cv2.hconcat([obs_left, obs_front, obs_right])
                        concat_imgs.append(concat_img)
                    dataset["obs3d"] = concat_imgs

            for idx in tqdm(range(num_traj)):
                file_name = ("%d.pt" % (file_count))
                t0 = idx*config["traj_steps"]
                t1 = t0+config["traj_steps"]
                for data_name in config["dataset"]:
                    path = os.path.join(out_dir, data_name, file_name)

                    if use_obs3_img_flag and data_name == "obs":
                        continue
                    if use_obs3d_img_flag and data_name == "obsd":
                        continue

                    if data_name == "pos":
                        traj_pos = dataset["pos"][t0:t1]
                        poses = []
                        init_pose = traj_pos[0].copy()
                        for idx, pose in enumerate(traj_pos):
                            trans_pose = transform_pose(pose, init_pose)
                            poses.append(trans_pose)
                        data = torch.tensor(poses, dtype=torch.float32)

                    elif data_name == "global_pos":
                        traj_pos = dataset["global_pos"][t0:t1]
                        poses = []
                        init_pose = traj_pos[0].copy()
                        for idx, pose in enumerate(traj_pos):
                            trans_pose = transform_pose(pose, init_pose)
                            poses.append(trans_pose)
                        data = torch.tensor(poses, dtype=torch.float32)

                    elif data_name == "goal":
                        traj_pos = dataset["pos"][t0:t1+config["goal_steps"]]

                        goals = []
                        for idx, pose in enumerate(traj_pos):
                            # if (idx+config["goal_steps"]) < len(traj_pos) and len(dataset["obs"]) > (t1+config["goal_steps"]):
                            goal = transform_pose(traj_pos[-1], pose)
                            goals.append(goal)
                        data = torch.tensor(goals, dtype=torch.float32)
                    elif data_name == "goal_obs":
                        # if (t1-1) < len(dataset["obs"]):
                        traj_goal_obs = dataset["obs"][t1+config["goal_steps"]-1]
                        data = torch.tensor(traj_goal_obs, dtype=torch.float32)
                    else:
                        traj_data = dataset[data_name][t0:t1]
                        data = torch.tensor(traj_data, dtype=torch.float32)

                    with open(path, "wb") as f:
                        torch.save(data, f)
                file_count += 1
        with open(os.path.join(out_dir, 'info.txt'), 'w') as f:
            info = config
            info['num_steps'] = num_steps * divide_count
            info['num_traj'] = num_traj * divide_count
            json.dump(info, f)

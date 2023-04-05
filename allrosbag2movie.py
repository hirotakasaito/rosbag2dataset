#!/usr/bin/python3

import os
import argparse
import json
import subprocess
from glob import iglob
from multiprocessing import Pool

parser = argparse.ArgumentParser()
parser.add_argument("-b", "--rosbag-dir", type=str, default="/share/private/27th/hirotaka_saito/bagfile/sq2/d_kan1/all3img/")
parser.add_argument('--image-topic', type=str, default='camera/color/image_raw/compressed')
parser.add_argument('--output-dir', type=str, default='/share/private/27th/hirotaka_saito/dataset/movie')
parser.add_argument('--frame-rate', type=int, default=30)
parser.add_argument('--num-core', type=int, default=5)
args = parser.parse_args()


def each_convert2mp4(bag_path):
    command = "python3 ./rosbag2movie.py --bagfile " +  bag_path + " --image-topic " + args.image_topic + " --output-dir " + args.output_dir + " --frame-rate " + str(args.frame_rate)

    proc = subprocess.run(command,shell=True,stdout=subprocess.PIPE,text=True)
    print(proc.check_returncode())
    print(proc.stdout)

def main():

    count = 1
    bag_paths = []
    for bag_path in iglob(os.path.join(args.rosbag_dir, "*")):
        bag_paths.append(bag_path)

    with Pool(args.num_core) as p:
        p.map(each_convert2mp4, bag_paths)


if __name__ == "__main__":
    main()

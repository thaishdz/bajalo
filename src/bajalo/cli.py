import argparse
from bajalo.downloader import download_video
 
def main():
    parser = argparse.ArgumentParser(prog="bajalo")
    parser.add_argument("url")
    args = parser.parse_args()
    download_video(args.url)
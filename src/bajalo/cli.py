import argparse

def main():
    parser = argparse.ArgumentParser(prog="bajalo")
    parser.add_argument("url")
    args = parser.parse_args()
    print(args.url)
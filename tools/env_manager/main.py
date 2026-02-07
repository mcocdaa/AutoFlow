import argparse
import os
import sys

# Add the parent directory to sys.path to allow running as script
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

from tools.env_manager.core import EnvManager

def main():
    parser = argparse.ArgumentParser(description="AutoFlow Environment Manager")
    parser.add_argument("command", choices=["install", "scan"], help="Command to execute")
    parser.add_argument("--scope", choices=["dev", "prod"], default="dev", help="Environment scope")
    parser.add_argument("--root", default=os.getcwd(), help="Root directory to scan")

    args = parser.parse_args()

    manager = EnvManager(root_dir=args.root, scope=args.scope)
    manager.scan()

    if args.command == "install":
        manager.install()

if __name__ == "__main__":
    main()

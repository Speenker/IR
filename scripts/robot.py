import argparse
import asyncio
import logging
import sys

from src.robot.config import load_robot_config
from src.robot.robot import Robot


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to robot YAML config")
    args = ap.parse_args()

    cfg = load_robot_config(args.config)
    robot = Robot(cfg)
    await robot.run()


if __name__ == "__main__":
    setup_logging()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)

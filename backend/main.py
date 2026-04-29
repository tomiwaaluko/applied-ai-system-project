from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from agents.orchestrator import CareerScopeOrchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CareerScope career intelligence pipeline.")
    parser.add_argument("--resume", required=True, help="Path to resume PDF.")
    jd_group = parser.add_mutually_exclusive_group(required=True)
    jd_group.add_argument("--jd", help="Job description URL.")
    jd_group.add_argument("--jd-text", help="Raw job description text.")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated reports.")
    return parser.parse_args()


async def async_main() -> None:
    load_dotenv()
    args = parse_args()
    jd_input = args.jd if args.jd is not None else args.jd_text
    orchestrator = CareerScopeOrchestrator(output_dir=Path(args.output_dir))
    await orchestrator.run(resume_path=args.resume, jd_input=jd_input)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

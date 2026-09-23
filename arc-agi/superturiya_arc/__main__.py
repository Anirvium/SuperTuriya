from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from .artifacts import atomic_json, provenance, verify_journal
from .config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENVIRONMENTS = PROJECT_ROOT / "environment_files"


def main():
    parser = argparse.ArgumentParser(description="SuperTuriya ARC-AGI-3 development and release tools")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "cache", "split"):
        command = sub.add_parser(name)
        command.add_argument("--environments", type=Path, default=DEFAULT_ENVIRONMENTS)
        if name == "cache":
            command.add_argument("--games", default="ls20,vc33,ft09")
        if name == "split":
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--seed", type=int, default=2026)
    play = sub.add_parser("run")
    play.add_argument("--config", type=Path, default=PROJECT_ROOT/"configs"/"explore.json")
    play.add_argument("--output", type=Path, required=True)
    play.add_argument("--environments", type=Path, default=DEFAULT_ENVIRONMENTS)
    play.add_argument("--games")
    play.add_argument("--split", type=Path)
    play.add_argument("--partition", choices=["development", "holdout"], default="development")
    play.add_argument("--max-actions", type=int)
    play.add_argument("--seed", type=int)
    play.add_argument("--profile", choices=["random", "explore", "reactive", "memory", "repair"])
    comparison = sub.add_parser("compare")
    comparison.add_argument("baseline", type=Path)
    comparison.add_argument("candidate", type=Path)
    comparison.add_argument("--output", type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("run_dir", type=Path)
    for name in ("verify-build", "push"):
        command = sub.add_parser(name)
        command.add_argument("directory", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("--config", type=Path, required=True)
    matrix.add_argument("--split", type=Path, required=True)
    matrix.add_argument("--partition", choices=["development", "holdout"], default="development")
    matrix.add_argument("--seeds", default="2026,2027,2028")
    matrix.add_argument("--profiles", default="memory,repair")
    matrix.add_argument("--output", type=Path, required=True)
    matrix.add_argument("--environments", type=Path, default=DEFAULT_ENVIRONMENTS)
    build = sub.add_parser("build")
    build.add_argument("--config", type=Path, default=PROJECT_ROOT/"configs"/"explore.json")
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--username", default="piyusha1234")
    build.add_argument("--accelerator", choices=["cpu", "t4", "p100", "rtx6000"], default="rtx6000")
    build.add_argument("--model-path")
    build.add_argument("--model-source", action="append", default=[])
    build.add_argument("--dataset-source", action="append", default=[])
    build.add_argument("--wheel-path")
    build.add_argument("--tensor-parallel", type=int, default=1)
    build.add_argument("--kernel-slug", default="notebook5326562b0c")
    build.add_argument("--title", default="notebook5326562b0c")
    sub.add_parser("doctor")
    args = parser.parse_args()
    if args.command == "doctor":
        print(json.dumps(provenance(), indent=2))
    elif args.command in {"list", "cache", "split"}:
        from .runtime import arcade
        arc = arcade("normal" if args.command in {"list", "cache"} else "offline",
                     args.environments, PROJECT_ROOT/"recordings"/"cache")
        ids = sorted(e.game_id for e in arc.get_environments())
        if args.command == "list":
            print(json.dumps(ids, indent=2))
        elif args.command == "split":
            from .evaluation import create_split
            print(json.dumps(create_split(ids, args.output, args.seed), indent=2))
        else:
            wanted = ids if args.games == "all" else args.games.split(",")
            for game_id in wanted:
                if not any(g == game_id or g.split("-")[0] == game_id for g in ids):
                    raise ValueError(f"unknown game: {game_id}")
                env = arc.make(game_id)
                if env is None:
                    raise RuntimeError(f"could not cache {game_id}")
                print(f"cached {env.info.game_id}")
            arc.close_scorecard()
            # Source bytes are cached by the SDK but never inspected by the agent.
    elif args.command == "run":
        from .runtime import run
        from .evaluation import load_split
        if args.games and args.split:
            raise ValueError("choose --games or --split")
        config = Config.load(args.config)
        for field in ("max_actions", "seed", "profile"):
            if getattr(args, field) is not None:
                config = replace(config, **{field: getattr(args, field)})
        games = load_split(args.split, args.partition) if args.split else (args.games.split(",") if args.games else None)
        report = run(config, args.output, args.environments, games)
        print(json.dumps({"status": report["status"], "report": str(args.output/"report.json"),
                          "sdk_score": (report["scorecard"] or {}).get("score")}, indent=2))
        if report["status"] != "complete":
            raise SystemExit(1)
    elif args.command == "compare":
        from .evaluation import compare
        print(json.dumps(compare(args.baseline, args.candidate, args.output), indent=2))
    elif args.command == "verify":
        from .release import verify_run
        print(json.dumps(verify_run(args.run_dir), indent=2))
    elif args.command in {"verify-build", "push"}:
        from .release import verify_build, push
        print(json.dumps((push if args.command == "push" else verify_build)(args.directory), indent=2))
    elif args.command == "matrix":
        from .runtime import run
        from .evaluation import load_split, compare
        config = Config.load(args.config)
        games = load_split(args.split, args.partition)
        profiles = args.profiles.split(",")
        seeds = [int(seed) for seed in args.seeds.split(",")]
        if len(set(profiles)) != len(profiles) or len(set(seeds)) != len(seeds):
            raise ValueError("matrix profiles and seeds must be unique")
        args.output.mkdir(parents=True, exist_ok=False)
        plan = {"profiles": profiles, "seeds": seeds, "games": games, "partition": args.partition,
                "split": json.loads(args.split.read_text()), "config": config.to_dict()}
        atomic_json(args.output/"plan.json", plan)
        results = []
        for seed in seeds:
            runs = []
            for profile in profiles:
                directory = args.output/f"{seed}-{profile}"
                report = run(replace(config, profile=profile, seed=seed), directory, args.environments, games)
                if report["status"] != "complete":
                    raise RuntimeError(f"matrix stopped on incomplete run: {directory}")
                runs.append(directory/"report.json")
            for candidate in runs[1:]:
                results.append(compare(runs[0], candidate))
            atomic_json(args.output/"comparisons.json", results)
        print(json.dumps({"output": str(args.output), "comparisons": len(results)}, indent=2))
    elif args.command == "build":
        from .notebook import build as build_notebook
        print(build_notebook(Config.load(args.config), args.output, args.username, args.accelerator,
                             args.model_path, args.model_source, args.dataset_source, args.wheel_path,
                             args.tensor_parallel, args.kernel_slug, args.title))


if __name__ == "__main__":
    main()

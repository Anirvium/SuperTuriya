from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from pathlib import Path
from textwrap import dedent

from .artifacts import atomic_json, source_manifest
from .config import Config


ACCELERATORS = {
    "cpu": {"notebook": "none", "machine": "", "gpu": False},
    "t4": {"notebook": "NvidiaTeslaT4", "machine": "NvidiaTeslaT4", "gpu": True},
    "p100": {"notebook": "NvidiaTeslaP100", "machine": "NvidiaTeslaP100", "gpu": True},
    "rtx6000": {
        "notebook": "NvidiaRtxPro6000",
        "machine": "NvidiaRtxPro6000",
        "gpu": True,
    },
}


def resolve_kaggle_input(
    input_root: Path,
    spec: str | None,
    marker: str,
    require_weights: bool = False,
) -> Path | None:
    """Resolve dataset and model assets across Kaggle's nested mount layouts."""
    if spec is None:
        return None
    if spec.startswith("/kaggle/input/"):
        candidate = Path(spec)
        if not candidate.exists():
            raise RuntimeError(f"Attached input path does not exist: {candidate}")
        return candidate

    hint = spec.split(":", 1)[1].lower()
    matches = sorted(
        path for path in input_root.rglob(marker)
        if hint in str(path).lower()
    )
    if require_weights:
        candidates = sorted({
            match.parent for match in matches
            if list(match.parent.glob("*.safetensors")) or list(match.parent.glob("*.bin"))
        })
        if len(candidates) == 1:
            return candidates[0]
    elif matches:
        return Path(os.path.commonpath([str(match.parent) for match in matches]))

    visible = sorted(str(path) for path in input_root.glob("**/config.json"))[:20]
    kind = "model directories" if require_weights else f"files matching {marker!r}"
    raise RuntimeError(
        f"Expected one mounted input for {spec!r}; found {len(matches)} {kind}. "
        f"Visible config paths (first 20): {visible}"
    )


def cell(source: str, kind: str = "code") -> dict:
    result = {"cell_type": kind, "metadata": {}, "source": source}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


def _asset_spec(value: str | None, label: str) -> None:
    if value is None:
        return
    if value.startswith("auto:") and re.fullmatch(r"auto:[A-Za-z0-9_.-]+", value):
        return
    if value.startswith("/kaggle/input/"):
        return
    raise ValueError(f"{label} must be /kaggle/input/... or auto:<mounted-input-hint>")


def build(
    config: Config,
    output: Path,
    username: str = "piyusha1234",
    accelerator: str = "rtx6000",
    model_path: str | None = None,
    model_sources=(),
    dataset_sources=(),
    wheel_path: str | None = None,
    tensor_parallel: int = 1,
    validation_games=(),
    kernel_slug: str = "notebook5326562b0c",
    title: str = "notebook5326562b0c",
):
    """Create a self-contained, offline Kaggle notebook and its CLI metadata."""
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", username):
        raise ValueError("invalid Kaggle username")
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", kernel_slug):
        raise ValueError("invalid Kaggle kernel slug")
    if accelerator not in ACCELERATORS:
        raise ValueError("unsupported accelerator")
    _asset_spec(model_path, "model path")
    _asset_spec(wheel_path, "wheel path")
    uses_model = config.profile not in {"random", "explore"}
    if uses_model and (not model_path or not config.model or not ACCELERATORS[accelerator]["gpu"]):
        raise ValueError("model notebook requires a mounted model, served name, and GPU")
    if uses_model and not model_sources:
        raise ValueError("model notebook requires an explicit Kaggle model source")
    if wheel_path and not dataset_sources:
        raise ValueError("offline wheel path requires an explicit Kaggle dataset source")
    if tensor_parallel not in (1, 2, 4):
        raise ValueError("tensor parallel must be 1, 2, or 4")
    validation_games = tuple(validation_games)
    if any(not re.fullmatch(r"[a-z0-9]{4}(?:-[a-f0-9]{8})?", game) for game in validation_games):
        raise ValueError("validation game IDs must be four lowercase alphanumerics with optional version")
    if len(validation_games) != len(set(validation_games)):
        raise ValueError("validation games must be unique")
    if output.exists() and any(output.iterdir()):
        raise ValueError("build directory must be empty; use a new version directory")
    output.mkdir(parents=True, exist_ok=True)

    root = Path(__file__).parent
    encoded = {p.name: base64.b64encode(p.read_bytes()).decode() for p in sorted(root.glob("*.py"))}
    hashes = source_manifest()
    settings = {
        "accelerator": accelerator,
        "model_path": model_path,
        "wheel_path": wheel_path,
        "tensor_parallel": tensor_parallel,
        "uses_model": uses_model,
        "validation_games": validation_games,
    }

    bootstrap = dedent(
        f"""\
        import json, os, pathlib, platform, subprocess, sys, time

        if sys.version_info < (3, 12):
            raise RuntimeError("ARC-AGI-3 requires Python 3.12+")
        NOTEBOOK_START = time.monotonic()
        EXPECTED_ACCELERATOR = {accelerator!r}
        os.environ.update(
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            HF_HUB_DISABLE_TELEMETRY="1",
            TOKENIZERS_PARALLELISM="false",
        )
        print("Python:", sys.version)
        print("Platform:", platform.platform())
        if EXPECTED_ACCELERATOR != "cpu":
            import torch
            if not torch.cuda.is_available():
                raise RuntimeError("GPU metadata was requested but CUDA is unavailable")
            gpu_name = torch.cuda.get_device_name(0)
            gpu_gib = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"GPU: {{gpu_name}} ({{gpu_gib:.1f}} GiB), torch={{torch.__version__}}, cuda={{torch.version.cuda}}")

        competition_roots = [
            pathlib.Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3"),
            pathlib.Path("/kaggle/input/arc-prize-2026-arc-agi-3"),
        ]
        competition_root = next((p for p in competition_roots if p.is_dir()), None)
        if competition_root is None:
            raise RuntimeError("ARC-AGI-3 competition data is not attached")
        wheel_dirs = sorted({{str(p.parent) for p in competition_root.rglob("arc_agi-*.whl")}})
        if not wheel_dirs:
            raise RuntimeError("The competition arc-agi wheel bundle was not found")
        command = [sys.executable, "-m", "pip", "install", "--no-index"]
        for directory in wheel_dirs:
            command += ["--find-links", directory]
        subprocess.run(command + ["arc-agi", "python-dotenv"], check=True, timeout=300)
        print("Official ARC runtime installed from competition inputs.")
        """
    )

    source_cell = (
        "import base64, hashlib\n"
        + "ENCODED = " + repr(encoded) + "\n"
        + "SOURCE_SHA256 = " + repr(hashes) + "\n"
        + "CONFIG = " + repr(config.to_dict()) + "\n"
        + "SETTINGS = " + repr(settings) + "\n"
        + dedent(
            """\
            source_root = pathlib.Path('/tmp/superturiya-arc-agi')
            package_root = source_root / 'superturiya_arc'
            package_root.mkdir(parents=True, exist_ok=True)
            for name, value in ENCODED.items():
                payload = base64.b64decode(value)
                if hashlib.sha256(payload).hexdigest() != SOURCE_SHA256[name]:
                    raise RuntimeError(f'Embedded source hash mismatch: {name}')
                (package_root/name).write_bytes(payload)
            sys.path.insert(0, str(source_root))

            from superturiya_arc.config import Config
            from superturiya_arc.observation import Action
            from superturiya_arc.programs import ProgramExecutor

            config = Config(**CONFIG)
            check = ProgramExecutor().run(
                'def analyze(data):\\n    return sum(data)', 'analyze', [[[1, 2, 3]]]
            )
            assert check == {'ok': True, 'values': [6]}, check
            assert Action.parse({'id': 6, 'x': 63, 'y': 0}, (6,)).x == 63
            print(f'Embedded SuperTuriya ARC source verified ({len(SOURCE_SHA256)} files).')
            print('Profile:', config.profile, '| parallel games:', config.max_parallel_games)
            """
        )
    )

    model_cell = dedent(
        """\
        import importlib.metadata, importlib.util, urllib.request
        from superturiya_arc.notebook import resolve_kaggle_input

        server = None
        model_log = None
        if SETTINGS['uses_model']:
            input_root = pathlib.Path('/kaggle/input')
            model_path = resolve_kaggle_input(
                input_root, SETTINGS['model_path'], 'config.json', require_weights=True
            )
            wheel_root = resolve_kaggle_input(
                input_root, SETTINGS['wheel_path'], '*.whl'
            ) if SETTINGS['wheel_path'] else None
            if wheel_root is not None:
                wheel_dirs = sorted({str(p.parent) for p in wheel_root.rglob('*.whl')})
                command = [sys.executable, '-m', 'pip', 'install', '--no-index', '--upgrade']
                for directory in wheel_dirs:
                    command += ['--find-links', directory]
                subprocess.run(command + ['vllm'], check=True, timeout=900)
            if importlib.util.find_spec('vllm') is None:
                raise RuntimeError('vLLM is unavailable; attach the configured offline wheelhouse')
            print('vLLM:', importlib.metadata.version('vllm'))
            print('Model path:', model_path)

            from urllib.parse import urlsplit
            port = urlsplit(config.endpoint).port or 8000
            model_log = open('/kaggle/working/model-server.log', 'w')
            serve_command = [
                sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
                '--model', str(model_path),
                '--served-model-name', config.model,
                '--host', '127.0.0.1',
                '--port', str(port),
                '--max-model-len', str(config.max_context_tokens),
                '--tensor-parallel-size', str(SETTINGS['tensor_parallel']),
                '--gpu-memory-utilization', '0.90',
                '--max-num-seqs', str(config.max_parallel_games),
                '--generation-config', 'vllm',
                '--trust-remote-code',
                '--enable-prefix-caching',
            ]
            if config.enable_thinking is not None:
                serve_command += ['--reasoning-parser', 'qwen3', '--tool-call-parser', 'qwen3_coder']
            server = subprocess.Popen(serve_command, stdout=model_log, stderr=subprocess.STDOUT)
            ready_by = min(time.monotonic()+1200, NOTEBOOK_START+config.total_seconds-config.reserve_seconds)
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            while time.monotonic() < ready_by:
                if server.poll() is not None:
                    raise RuntimeError('Model server exited; inspect model-server.log')
                try:
                    with opener.open(config.endpoint.rstrip('/')+'/models', timeout=3) as response:
                        advertised = [m['id'] for m in json.load(response)['data']]
                    if config.model not in advertised:
                        raise RuntimeError('Model server name mismatch')
                    break
                except (OSError, ValueError):
                    time.sleep(2)
            else:
                server.terminate()
                raise RuntimeError('Local model did not become ready within 20 minutes')

            from superturiya_arc.provider import LocalModel, parse_response
            probe, _ = LocalModel(config).complete([
                {'role': 'system', 'content': 'Return only valid JSON.'},
                {'role': 'user', 'content': 'Return {"actions":[{"id":1}]}.'},
            ], 120)
            Action.parse(parse_response(probe)['actions'][0], (1,))
            print('Local model readiness probe passed.')
        """
    )

    run_cell = dedent(
        """\
        from superturiya_arc.runtime import run

        rerun = os.environ.get('KAGGLE_IS_COMPETITION_RERUN', '').lower() in {'1', 'true', 'yes'}
        try:
            if rerun:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                gateway_ready = False
                wait_until = min(
                    time.monotonic()+600,
                    NOTEBOOK_START+config.total_seconds-config.reserve_seconds,
                )
                while time.monotonic() < wait_until:
                    try:
                        request = urllib.request.Request(
                            'http://gateway:8001/api/games',
                            headers={'X-API-Key': 'test-key-123'},
                        )
                        with opener.open(request, timeout=5) as response:
                            gateway_ready = bool(json.load(response))
                        if gateway_ready:
                            break
                    except (OSError, ValueError):
                        pass
                    time.sleep(2)
                if not gateway_ready:
                    raise RuntimeError('Competition gateway unavailable')
                report = run(
                    config,
                    pathlib.Path('/kaggle/working/arc-agi-run'),
                    pathlib.Path('/tmp/unused-environments'),
                    mode='competition',
                    gateway='http://gateway:8001',
                    run_deadline=NOTEBOOK_START+config.total_seconds,
                )
                if report['status'] != 'complete':
                    raise RuntimeError('Run incomplete; inspect arc-agi-run/report.json')
                if not pathlib.Path('/kaggle/working/submission.parquet').is_file():
                    raise RuntimeError('Gateway did not produce submission.parquet')
            else:
                validation_games = list(SETTINGS.get('validation_games', ()))
                if validation_games:
                    public_environments = competition_root / 'environment_files'
                    if not public_environments.is_dir():
                        raise RuntimeError('Official public environment files are unavailable')
                    report = run(
                        config,
                        pathlib.Path('/kaggle/working/arc-agi-run'),
                        public_environments,
                        game_ids=validation_games,
                        mode='offline',
                        run_deadline=NOTEBOOK_START+config.total_seconds,
                    )
                    if report['status'] != 'complete':
                        raise RuntimeError('Public benchmark incomplete; inspect arc-agi-run/report.json')
                    print(
                        'Public benchmark passed:',
                        report['scorecard'].get('score'),
                        '| games:', len(report['games']),
                    )
                import pandas as pd
                pd.DataFrame(
                    [['1_0', '1', True, 1]],
                    columns=['row_id', 'game_id', 'end_of_game', 'score'],
                ).to_parquet('/kaggle/working/submission.parquet', index=False)
                print('Kaggle commit-mode validation passed; placeholder submission created.')
        finally:
            if server is not None:
                server.terminate()
                try:
                    server.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    server.kill()
            if model_log is not None:
                model_log.close()
        """
    )

    accel = ACCELERATORS[accelerator]
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
            "language_info": {"name": "python", "version": "3.12"},
            "kaggle": {
                "accelerator": accel["notebook"],
                "isInternetEnabled": False,
                "isGpuEnabled": accel["gpu"],
            },
        },
        "cells": [
            cell(
                "# SuperTuriya ARC-AGI-3\n\n"
                "Self-contained offline Kaggle build. Source is generated from `arc-agi/`; "
                "do not edit this notebook directly.",
                "markdown",
            ),
            cell(bootstrap),
            cell(source_cell),
            cell(model_cell),
            cell(run_cell),
        ],
    }
    for index, entry in enumerate(notebook["cells"]):
        entry["id"] = f"superturiya-{index}"
        if entry["cell_type"] == "code":
            compile(entry["source"], f"cell-{index}", "exec")

    metadata = {
        "id": f"{username}/{kernel_slug}",
        "title": title,
        "code_file": "submission.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": accel["gpu"],
        "enable_tpu": False,
        "enable_internet": False,
        "machine_shape": accel["machine"],
        "keywords": [],
        "dataset_sources": list(dataset_sources),
        "model_sources": list(model_sources),
        "kernel_sources": [],
        "competition_sources": ["arc-prize-2026-arc-agi-3"],
    }
    atomic_json(output/"submission.ipynb", notebook)
    atomic_json(output/"kernel-metadata.json", metadata)
    atomic_json(
        output/"build-manifest.json",
        {
            "schema": "superturiya-arc-agi-build-v1",
            "config": config.to_dict(),
            "settings": settings,
            "kernel_id": metadata["id"],
            "source_sha256": hashes,
            "notebook_sha256": hashlib.sha256((output/"submission.ipynb").read_bytes()).hexdigest(),
            "status": "built_not_submitted",
            "kaggle_execution_verified": False,
        },
    )
    return output

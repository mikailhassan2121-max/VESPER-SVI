import argparse
import asyncio
import json
from datetime import date

from vesper.config import Settings


def main():
    parser = argparse.ArgumentParser(prog="vesper")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run")
    commands.add_parser("stop")
    commands.add_parser("check")
    validate = commands.add_parser("validate-live")
    validate.add_argument("--seconds", type=int, default=120)
    historical = commands.add_parser("download")
    historical.add_argument("--start", type=date.fromisoformat, required=True)
    historical.add_argument("--end", type=date.fromisoformat, required=True)
    dataset = commands.add_parser("build-dataset")
    dataset.add_argument("--output", required=True)
    training = commands.add_parser("train")
    training.add_argument("--dataset", required=True)
    training.add_argument("--locked-start", required=True)
    playback = commands.add_parser("replay")
    playback.add_argument("--recording", required=True)
    playback.add_argument("--session", type=date.fromisoformat, required=True)
    playback.add_argument("--output", required=True)
    playback.add_argument("--model")
    export = commands.add_parser("export-replay")
    export.add_argument("--session", type=date.fromisoformat, required=True)
    export.add_argument("--output", required=True)
    args = parser.parse_args()
    settings = Settings()
    settings.prepare()
    if args.command == "run":
        import uvicorn
        stop_file = settings.data_dir / "stop.request"

        async def serve():
            server = uvicorn.Server(uvicorn.Config("vesper.api:create_app", factory=True,
                                                   host="127.0.0.1", port=8787, workers=1))
            stop_file.unlink(missing_ok=True)

            async def monitor():
                while not server.should_exit:
                    if stop_file.exists():
                        server.should_exit = True
                        stop_file.unlink(missing_ok=True)
                        return
                    await asyncio.sleep(.5)
            watcher = asyncio.create_task(monitor())
            try:
                await server.serve()
            finally:
                watcher.cancel()
                await asyncio.gather(watcher, return_exceptions=True)
        asyncio.run(serve())
    elif args.command == "stop":
        (settings.data_dir / "stop.request").touch()
        print("Graceful shutdown requested.")
    elif args.command == "check":
        from vesper.calendar import Calendar, utcnow
        from vesper.storage import Store
        store = Store(settings.data_dir / "vesper.sqlite")
        store.close()
        print(json.dumps({"configuration": "PASS", "calendar": "PASS", "database": "PASS",
                          "next_signal": Calendar().upcoming(utcnow()).signal.isoformat(),
                          "credentials_configured": bool(settings.massive_api_key.get_secret_value()),
                          "production_validated": False}, indent=2))
    elif args.command == "validate-live":
        from vesper.validation import validate_live
        report, evidence = asyncio.run(validate_live(settings, max(1, args.seconds)))
        print(json.dumps({"checks": report, "evidence": evidence}, indent=2))
        raise SystemExit(0 if report["LIVE PIPELINE"] == "PASS" else 2)
    elif args.command == "train":
        from vesper.modeling import train
        print(json.dumps(train(args.dataset, settings.model_dir, args.locked_start), indent=2))
    elif args.command == "replay":
        from vesper.replay import replay
        print(json.dumps(asyncio.run(replay(settings, args.recording, args.session, args.output, args.model)), indent=2))
    elif args.command == "export-replay":
        from vesper.replay import export_recording
        print(json.dumps(export_recording(settings.data_dir / "vesper.sqlite", args.session, args.output), indent=2))
    elif args.command == "build-dataset":
        from vesper.dataset import build_dataset
        print(json.dumps(build_dataset(settings.data_dir, args.output), indent=2))
    elif args.command == "download":
        from vesper.history import download
        from vesper.provider import Massive

        async def acquire():
            provider = Massive(settings.massive_api_key.get_secret_value())
            try:
                await download(provider, settings.data_dir, args.start, args.end)
            finally:
                await provider.close()
        asyncio.run(acquire())


if __name__ == "__main__":
    main()

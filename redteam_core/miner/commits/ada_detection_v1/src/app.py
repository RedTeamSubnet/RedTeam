import sys
import logging
import pathlib
from pathlib import Path

from fastapi import FastAPI, Body, HTTPException
from data_types import MinerInput, MinerOutput, DetectionFilePM


logger = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S %z",
    format="[%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d]: %(message)s",
)


app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/solve", response_model=MinerOutput)
def solve(miner_input: MinerInput = Body(...)) -> MinerOutput:

    logger.info(f"Retrieving detection files...")
    _miner_output: MinerOutput
    try:
        _src_dir = pathlib.Path(__file__).parent.resolve()
        _detections_dir = _src_dir / "detections"
        _detection_paths: list[Path] = list(_detections_dir.glob("*.js"))

        _detection_files: list[DetectionFilePM] = []
        for _detection_path in _detection_paths:
            with open(_detection_path, "r") as _detection_file:
                _detection_file_pm = DetectionFilePM(
                    file_name=_detection_path.name, content=_detection_file.read()
                )
                _detection_files.append(_detection_file_pm)

        _miner_output = MinerOutput(detection_files=_detection_files)
        logger.info(f"Successfully retrieved detection files.")
    except Exception as err:
        logger.error(f"Failed to retrieve detection files: {str(err)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve detection files."
        )

    return _miner_output


__all__ = ["app"]

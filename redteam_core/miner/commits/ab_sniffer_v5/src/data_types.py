from typing import Optional

from pydantic import BaseModel, Field, constr, field_validator


class MinerInput(BaseModel):
    random_val: Optional[
        constr(strip_whitespace=True, min_length=4, max_length=64)  # type: ignore
    ] = Field(
        title="Random Value",
        description="Random value to prevent caching.",
        examples=["a1b2c3d4e5f6g7h8"],
    )


class DetectionFilePM(BaseModel):
    file_name: str = Field(
        ...,
        min_length=4,
        max_length=64,
        title="File Name",
        description="Name of the file.",
        examples=["detect.js"],
    )
    content: str = Field(
        ...,
        min_length=2,
        title="File Content",
        description="Content of the file as a string.",
        examples=["console.log('browser');"],
    )


class MinerOutput(BaseModel):
    detection_files: list[DetectionFilePM] = Field(
        ...,
        title="Detection JS Files",
        description="List of detection JS files for the challenge.",
    )

    @field_validator("detection_files", mode="after")
    @classmethod
    def _check_detection_files(
        cls, val: list[DetectionFilePM]
    ) -> list[DetectionFilePM]:
        for _miner_file_pm in val:
            _content_lines = _miner_file_pm.content.splitlines()
            if len(_content_lines) > 500:
                raise ValueError(
                    f"`{_miner_file_pm.file_name}` file contains too many lines, should be <= 500 lines!"
                )

        return val


__all__ = [
    "MinerInput",
    "DetectionFilePM",
    "MinerOutput",
]

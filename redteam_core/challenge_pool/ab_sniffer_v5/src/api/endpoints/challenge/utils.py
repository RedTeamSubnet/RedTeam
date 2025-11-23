import os
import random
import subprocess

from docker import DockerClient
from docker.types import Ulimit
from docker.models.networks import Network
from pydantic import validate_call

from api.config import config
from api.endpoints.challenge.schemas import MinerOutput
from api.logger import logger


@validate_call
def copy_detection_files(miner_output: MinerOutput, detections_dir: str) -> None:

    logger.info(f"Copying detection files from {detections_dir}")
    try:
        os.makedirs(detections_dir, exist_ok=True)
        for _detection_file_pm in miner_output.detection_files:
            _detection_path = os.path.join(detections_dir, _detection_file_pm.file_name)
            with open(_detection_path, "w") as _detection_file:
                _detection_file.write(_detection_file_pm.content)

        logger.success("Successfully copied detection files.")

    except Exception as err:
        logger.error(f"Failed to copy detection files: {err}!")
        raise

    return


def run_bot_container(
    docker_client: DockerClient,
    image_name: str = "bot:latest",
    container_name: str = "bot_container",
    network_name: str = "framework_network",
    ulimit: int = 32768,
    **kwargs,
) -> str:

    try:
        # Network setup from the provided function
        _networks = docker_client.networks.list(names=[network_name])
        _network: Network
        if not _networks:
            _network = docker_client.networks.create(
                name=network_name, driver="bridge", internal=True
            )
        else:
            _network = docker_client.networks.get(network_name)

        _network_id = _network.id
        if _network_id is None:
            raise RuntimeError("Failed to determine Docker network ID!")

        _network_info = docker_client.api.inspect_network(net_id=_network_id)
        _gateway_ip = _network_info["IPAM"]["Config"][0]["Gateway"]

        _ulimit_nofile = Ulimit(name="nofile", soft=ulimit, hard=ulimit)

        _web_url = f"http://{_gateway_ip}:{config.api.port}/_web"

        _waiting_time = round(random.uniform(3, 9), 4)
        logger.info(
            f"Running {image_name} docker container with {_waiting_time}s wait time to connect to {_web_url}"
        )
        _container = docker_client.containers.run(
            image=image_name,
            name=container_name,
            ulimits=[_ulimit_nofile],
            environment={"ABS_WEB_URL": _web_url, "RANDOM_WAIT": str(_waiting_time)},
            network=network_name,
            detach=True,
            **kwargs,
        )

        # Stream container logs
        try:
            for log in _container.logs(stream=True):
                logger.debug(log.decode().strip())
        except Exception as e:
            logger.error(f"Error streaming logs: {e}")

        logger.info(f"Successfully ran {image_name} docker container.")

    except Exception as err:
        logger.error(f"Failed to run {image_name} docker: {str(err)}!")
        raise

    return _container


@validate_call
def stop_container(container_name: str = "detector_container") -> None:
    logger.info(f"Stopping container '{container_name}'")
    try:
        subprocess.run(
            ["sudo", "docker", "rm", "-f", container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.success(f"Successfully stopped container '{container_name}'.")
    except Exception:
        logger.debug(f"Failed to stop container '{container_name}'!")
        pass  # Continue even if container doesn't exist

    return


__all__ = [
    "copy_detection_files",
    "run_bot_container",
    "stop_container",
]

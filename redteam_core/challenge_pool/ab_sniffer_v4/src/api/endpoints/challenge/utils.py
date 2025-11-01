# -*- coding: utf-8 -*-

import os
import time
import subprocess
import random

import docker
import threading
from docker import DockerClient
from pydantic import validate_call

from api.config import config

from api.endpoints.challenge.schemas import MinerOutput
from api.logger import logger


def gen_ran_framework_sequence() -> list:
    frameworks = config.challenge.framework_images
    repeated_frameworks = []
    for _ in range(config.challenge.repeated_framework_count):
        repeated_frameworks.extend(frameworks)

    random.shuffle(repeated_frameworks)
    return repeated_frameworks


@validate_call
def copy_detector_file(miner_output: MinerOutput, templates_dir: str) -> None:
    logger.info("Copying detection file...")
    try:
        _detection_template_dir = os.path.join(templates_dir, "static", "detection")
        _detection_js_path = os.path.join(_detection_template_dir, "detection.js")

        # Ensure directory exists
        os.makedirs(_detection_template_dir, exist_ok=True)

        with open(_detection_js_path, "w") as _detection_js_file:
            _detection_js_file.write(miner_output.detection_js)
        logger.success("Successfully copied detection.js files.")

        try:
            logger.info("Checking detection.js format...")

        except Exception as err:
            logger.error(f"Failed to check detection.js format: {err}!")
            raise

    except Exception as err:
        logger.error(f"Failed to copy detection.js files: {err}!")
        raise

    return


def get_submission_file_size(templates_dir: str) -> int:
    _detection_template_dir = os.path.join(templates_dir, "static", "detection")
    _detection_js_path = os.path.join(_detection_template_dir, "detection.js")
    _file_size = os.path.getsize(_detection_js_path)
    return _file_size


def run_bot_container(
    docker_client: DockerClient,
    image_name: str = "bot:latest",
    container_name: str = "bot_container",
    network_name: str = "framework_network",
    ulimit: int = 32768,
    **kwargs,
) -> str:
    logger.info(f"Running {image_name} docker container...")
    detected_driver = None

    try:
        # Network setup from the provided function
        _networks = docker_client.networks.list(names=[network_name])
        _network = None
        if not _networks:
            _network = docker_client.networks.create(name=network_name, driver="bridge")
        else:
            _network = docker_client.networks.get(network_name)

        _network_info = docker_client.api.inspect_network(_network.id)
        _subnet = _network_info["IPAM"]["Config"][0]["Subnet"]
        _gateway_ip = _network_info["IPAM"]["Config"][0]["Gateway"]

        # Apply network limitations
        subprocess.run(
            [
                "sudo",
                "iptables",
                "-I",
                "FORWARD",
                "-s",
                _subnet,
                "!",
                "-d",
                _subnet,
                "-j",
                "DROP",
            ]
        )
        subprocess.run(
            [
                "sudo",
                "iptables",
                "-t",
                "nat",
                "-I",
                "POSTROUTING",
                "-s",
                _subnet,
                "-j",
                "RETURN",
            ]
        )

        # Stop any existing container with the same name
        stop_container(container_name=container_name)
        time.sleep(1)

        # Set up ulimit configuration
        _ulimit_nofile = docker.types.Ulimit(name="nofile", soft=ulimit, hard=ulimit)

        # Generate a temporary container ID for this run
        _container_id = f"run_{int(time.time())}"
        _log_path = f"/tmp/driver_type_{_container_id}.txt"
        _web_url = f"http://{_gateway_ip}:{config.api.port}/_web"

        # Mount volume for easier file access
        volumes = {"/tmp": {"bind": "/host_tmp", "mode": "rw"}}

        # Run the container

        _container = docker_client.containers.run(
            image=image_name,
            name=container_name,
            ulimits=[_ulimit_nofile],
            environment={
                "ABS_WEB_URL": _web_url,
                "CONTAINER_ID": _container_id,
                "DETECTED_DRIVER_PATH": _log_path,
                "HOST_DRIVER_PATH": f"/host_tmp/driver_type_{_container_id}.txt",
            },
            volumes=volumes,
            network=network_name,
            detach=True,
            **kwargs,
        )

        # Stream container logs
        log_thread = threading.Thread(target=stream_container_logs, args=(_container,))
        log_thread.daemon = True
        log_thread.start()

        # Poll for driver type file (both inside container and in host-mounted volume)
        _poll_timeout = 60  # Longer timeout
        _poll_interval = 2  # Seconds
        _elapsed = 0

        while _elapsed < _poll_timeout:
            # Check host-mounted file first
            host_driver_path = f"/tmp/driver_type_{_container_id}.txt"
            if os.path.exists(host_driver_path):
                try:
                    with open(host_driver_path, "r") as f:
                        detected_driver = f.read().strip()
                        if detected_driver:  # Ensure we have a non-empty result
                            logger.info(
                                f"Driver type found in host volume: {detected_driver}"
                            )
                            break
                        else:
                            logger.warning(
                                "Empty driver type file found in host volume"
                            )
                except Exception as e:
                    logger.warning(f"Error reading host driver file: {str(e)}")

            # Update container status
            _container.reload()

            logger.info(f"Driver type not found, retrying... ({_elapsed}s)")
            time.sleep(_poll_interval)
            _elapsed += _poll_interval

        # Clean up
        _container.stop()
        # ~ TODO: We need to stop the container not remove it
        _container.remove(force=True)
        logger.info(f"Successfully ran {image_name} docker container.")

    except Exception as err:
        logger.error(f"Failed to run {image_name} docker: {str(err)}!")
        raise

    return detected_driver


def stream_container_logs(container):
    try:
        for log in container.logs(stream=True):
            logger.info(log.decode().strip())
    except Exception as e:
        logger.error(f"Error streaming logs: {e}")


@validate_call
def stop_container(container_name: str = "detector_container") -> None:
    logger.info(f"Stopping container '{container_name}'...")
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
    "copy_detector_file",
    "run_bot_container",
    "stop_container",
    "gen_ran_framework_sequence",
]

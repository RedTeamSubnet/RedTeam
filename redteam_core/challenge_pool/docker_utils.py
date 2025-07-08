"""
Docker Utilities for Challenge Evaluation System

This module provides specialized Docker utilities for managing challenge evaluation containers
and miner solution containers in a secure, isolated environment. It handles container lifecycle,
health checking, networking, and resource management.

Key Assumptions:
1. Container Types:
   - Challenge containers: Provide task generation and evaluation endpoints
   - Solution containers: Process tasks and return outputs

2. Expected Endpoints:
   Challenge Containers:
   - /task: Generates task inputs
   - /score: Scores solution outputs
   - /compare: Compares two outputs for the same input
   - /health: Container health check

   Solution Containers:
   - /solve: Processes inputs and returns outputs
   - /health: Container health check

3. Security:
   - All containers run in isolated networks
   - Internet access is blocked by default
   - Resource limits are enforced
   - Container images must include SHA256 digests

4. Resource Management:
   - Containers are cleaned up after use
   - Resource limits (CPU, memory, GPU) are configurable
   - Proper error handling and logging
"""

import copy
import re
import subprocess
import time
from typing import List, Optional, Tuple, Union

import bittensor as bt
import docker
import docker.models.containers
import docker.types
import requests


def run_container(
    client: docker.DockerClient,
    image: str,
    **container_run_kwargs,
) -> docker.models.containers.Container:
    """
    Runs a Docker container with specified configuration.

    Args:
        client: Docker client instance
        image: Docker image name
        **container_run_kwargs: Additional container run arguments

    Returns:
        Container instance
    """
    # Create copy to avoid modifying original kwargs
    run_kwargs = copy.deepcopy(container_run_kwargs)

    # Prepare DeviceRequest
    if "device_requests" in run_kwargs:
        device_requests = run_kwargs.pop("device_requests")
        run_kwargs["device_requests"] = [
            docker.types.DeviceRequest(**device_request)
            for device_request in device_requests
        ]

    return client.containers.run(image, **run_kwargs)


# MARK: SETUP


def create_docker_client() -> docker.DockerClient:
    """Creates and returns a Docker client instance."""
    return docker.from_env()


def build_challenge_image(
    client: docker.DockerClient, challenge_name: str, build_path: str
) -> None:
    """
    Builds a challenge container image with proper tagging.

    Args:
        client: Docker client instance
        challenge_name: Name/tag for the challenge image
        build_path: Path to the challenge Dockerfile directory
    """
    try:
        try:
            subprocess.run(
                ["docker", "build", "--tag", challenge_name, "--rm", build_path],
                check=True,
                capture_output=True,
                text=True,
            )
            bt.logging.success(f"Successfully built challenge image: {challenge_name}")
        except subprocess.CalledProcessError as e:
            bt.logging.error(f"Failed to build challenge image: {e.stderr}")
            res = client.images.build(path=build_path, tag=challenge_name, rm=True)

            bt.logging.info(f"Successfully built challenge image: {challenge_name}")
            bt.logging.info(res)
    except Exception as e:
        bt.logging.error(f"Failed to build challenge image: {e}")
        raise


def create_network(
    client: docker.DockerClient,
    network_name: str,
    allow_internet: bool = False,
) -> None:
    """
    Creates a Docker network with configurable internet access control.

    Args:
        client: Docker client instance
        network_name: Name for the network
        allow_internet: If False, blocks internet access for containers in this network (default: False)

    The function creates a bridge network and sets up appropriate iptables rules
    for network isolation if internet access is blocked.
    """
    try:
        # Check if network exists
        networks = client.networks.list(names=[network_name])
        if not networks:
            network = client.networks.create(name=network_name, driver="bridge")
            bt.logging.info(f"Network '{network_name}' created successfully.")
        else:
            network = client.networks.get(network_name)
            bt.logging.info(f"Network '{network_name}' already exists.")

        if not allow_internet:
            # Set up network isolation
            network_info = client.api.inspect_network(network.id)
            subnet = network_info["IPAM"]["Config"][0]["Subnet"]

            # Define iptables rules for network isolation
            # fmt: off
            iptables_commands = [
                ["iptables", "-I", "FORWARD", "-s", subnet, "!", "-d", subnet, "-j", "DROP"],
                ["iptables", "-t", "nat", "-I", "POSTROUTING", "-s", subnet, "-j", "RETURN"]
            ]
            # fmt: on

            # Apply iptables rules
            for cmd in iptables_commands:
                try:
                    # Try with sudo first
                    subprocess.run(["sudo"] + cmd, check=True)
                except subprocess.CalledProcessError:
                    # Fallback without sudo if that fails
                    subprocess.run(cmd, check=True)

            bt.logging.info(
                f"Network '{network_name}' configured with internet access blocked"
            )
        else:
            bt.logging.info(
                f"Network '{network_name}' configured with internet access allowed"
            )

    except docker.errors.APIError as e:
        bt.logging.error(f"Failed to create/configure network: {e}")
        raise
    except subprocess.CalledProcessError as e:
        bt.logging.error(f"Failed to set up network isolation rules: {e}")
        raise
    except Exception as e:
        bt.logging.error(f"Unexpected error creating network: {e}")
        raise


# MARK: CLEANING

def remove_container(
    client: docker.DockerClient,
    container_name: str,
    stop_timeout: int = 10,
    force: bool = True,
    remove_volumes: bool = True,
    max_retries: int = 12,
) -> bool:
    """
    Safely stops and removes a Docker container with retries and comprehensive error handling.

    Args:
        client: Docker client instance
        container_name: Name of the container to remove
        stop_timeout: Timeout in seconds for stopping the container (default: 10)
        force: Whether to force remove the container (default: True)
        remove_volumes: Whether to remove associated volumes (default: True)
        max_retries: Maximum number of removal attempts (default: 3)

    Returns:
        bool: True if container was successfully removed or doesn't exist,
              False if removal failed after retries
    """
    try:
        containers = client.containers.list(all=True)
    except Exception as e:
        bt.logging.error(f"Failed to list containers: {str(e)}")
        return False

    target_container = None
    for container in containers:
        if container.name == container_name:
            target_container = container
            break

    if not target_container:
        bt.logging.info(f"Container '{container_name}' not found")
        return True

    # Try to stop container if running
    try:
        target_container.reload()
        if target_container.status != "exited":
            bt.logging.info(f"Stopping container '{container_name}'")
            subprocess.run(
                ["sudo", "docker", "stop", "-t", str(stop_timeout), container_name],
            )
    except (docker.errors.NotFound, docker.errors.APIError) as e:
        bt.logging.info(f"Container stop status: {str(e)}")
    except Exception as e:
        bt.logging.warning(f"Error stopping container: {str(e)}")

    # Attempt removal with retries
    for attempt in range(max_retries):
        try:
            # target_container.kill()
            target_container.remove(force=force, v=remove_volumes)
            bt.logging.info(f"Container '{container_name}' removed successfully")
            return True
        except (docker.errors.NotFound, docker.errors.APIError) as e:
            bt.logging.info(f"Container remove attempt {attempt + 1} status: {str(e)}")
            if isinstance(e, docker.errors.NotFound):
                return True
        except Exception as e:
            bt.logging.warning(
                f"Error removing container (attempt {attempt + 1}/{max_retries}): {str(e)}"
            )

        if attempt < max_retries - 1:
            time.sleep(2**attempt)  # Exponential backoff

    bt.logging.error(
        f"Failed to remove container '{container_name}' after {max_retries} attempts"
    )
    return False


def remove_container_by_port(client: docker.DockerClient, port: int) -> None:
    """
    Removes all containers using a specific port.

    Args:
        client: Docker client instance
        port: Port number to match
    """
    containers = client.containers.list(all=True)
    for container in containers:
        try:
            container_ports = container.attrs["NetworkSettings"]["Ports"]
            if any([str(port) in p for p in container_ports]):
                container.remove(force=True)
                bt.logging.info(f"Removed container {container.name}")
        except Exception as e:
            bt.logging.error(f"Error processing container {container.name}: {e}")


def clean_docker_resources(
    client: docker.DockerClient,
    remove_containers: bool = True,
    remove_images: bool = True,
    prune_volumes: bool = True,
    remove_networks: bool = False,
    prune_builds: bool = False,
) -> None:
    """
    Cleans up Docker resources.

    Args:
        client: Docker client instance
        remove_containers: Whether to remove stopped containers
        remove_images: Whether to remove dangling images
        remove_networks: Whether to remove unused networks
        prune_builds: Whether to prune build cache
    """
    try:
        if remove_containers:
            for container in client.containers.list(all=True):
                if container.status in ["exited", "dead"]:
                    bt.logging.info(
                        f"Removing container {container.name} ({container.id})..."
                    )
                    container.remove(force=True)

        if remove_images:
            # Delete all dangling images
            bt.logging.info("Removing dangling images...")
            for image in client.images.list(filters={"dangling": True}):
                bt.logging.info(f"Removing image {image.id}...")
                client.images.remove(image.id, force=True, noprune=False)

        # Delete unused resources (volumes, build cache)
        if prune_volumes:
            bt.logging.info("Pruning volumes...")
            client.volumes.prune()

        if remove_networks:
            bt.logging.info("Pruning networks...")
            client.networks.prune()

        if prune_builds:
            bt.logging.info("Pruning build cache...")
            client.api.prune_builds()

        bt.logging.info("Docker resources cleaned up successfully")
    except Exception as e:
        bt.logging.error(f"Error cleaning Docker resources: {e}")


def validate_image_digest(image: str) -> bool:
    """
    Validates that a Docker image includes a SHA256 digest.

    Args:
        image: Docker image name with digest

    Returns:
        bool: True if digest is valid
    """
    digest_pattern = r".+@sha256:[a-fA-F0-9]{64}$"
    if not re.match(digest_pattern, image):
        bt.logging.error(
            f"Invalid image format: {image}. Must include a SHA256 digest."
        )
        return False
    return True

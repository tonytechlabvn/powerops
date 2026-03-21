"""Resolve latest AMI ID for a given AWS region using boto3 SSM.

AWS publishes official latest AMI IDs as public SSM parameters.
No special permissions needed beyond ssm:GetParameter on public namespace.
"""
from __future__ import annotations

import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

# SSM parameter paths for official AMIs (AWS-maintained public params)
_AMI_SSM_PARAMS: dict[str, str] = {
    "amazon-linux-2023": "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64",
    "ubuntu-22.04": "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id",
}

# Default SSH user per OS type (for ssh_command output)
SSH_USERS: dict[str, str] = {
    "amazon-linux-2023": "ec2-user",
    "ubuntu-22.04": "ubuntu",
}


def resolve_ami(region: str, os_type: str = "amazon-linux-2023") -> str:
    """Query AWS SSM Parameter Store for the latest official AMI ID.

    Args:
        region: AWS region (e.g. "ap-southeast-1").
        os_type: One of "amazon-linux-2023" or "ubuntu-22.04".

    Returns:
        AMI ID string (e.g. "ami-0abcdef1234567890").

    Raises:
        ValueError: If os_type is not supported.
        RuntimeError: If AWS API call fails.
    """
    param_name = _AMI_SSM_PARAMS.get(os_type)
    if not param_name:
        raise ValueError(
            f"Unsupported os_type: {os_type}. Use: {list(_AMI_SSM_PARAMS.keys())}"
        )

    try:
        ssm = boto3.client("ssm", region_name=region)
        resp = ssm.get_parameter(Name=param_name)
        ami_id = resp["Parameter"]["Value"]
        logger.info("Resolved AMI for %s in %s: %s", os_type, region, ami_id)
        return ami_id
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"Failed to resolve AMI for {os_type} in {region}: {exc}") from exc


def get_ssh_user(os_type: str = "amazon-linux-2023") -> str:
    """Return the default SSH username for a given OS type."""
    return SSH_USERS.get(os_type, "ec2-user")

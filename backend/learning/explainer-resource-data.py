"""Static explanation data for the top 20 Terraform resource types.

Imported by explainer.py via importlib — do not import this module directly.
Each entry: title, what, key_args, cost_note, docs.
"""
from __future__ import annotations

RESOURCE_EXPLANATIONS: dict[str, dict] = {
    "aws_instance": {
        "title": "EC2 Instance",
        "what": "A virtual machine running in AWS.",
        "key_args": ["ami", "instance_type", "subnet_id", "vpc_security_group_ids", "key_name"],
        "cost_note": "Billed per second while running. t3.micro is free-tier eligible.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/instance",
    },
    "aws_vpc": {
        "title": "VPC (Virtual Private Cloud)",
        "what": "An isolated virtual network in AWS. All other network resources live inside it.",
        "key_args": ["cidr_block", "enable_dns_hostnames", "enable_dns_support"],
        "cost_note": "VPCs themselves are free; NAT gateways and endpoints are not.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc",
    },
    "aws_subnet": {
        "title": "VPC Subnet",
        "what": "A range of IP addresses within a VPC, scoped to one Availability Zone.",
        "key_args": ["vpc_id", "cidr_block", "availability_zone", "map_public_ip_on_launch"],
        "cost_note": "Subnets are free.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/subnet",
    },
    "aws_s3_bucket": {
        "title": "S3 Bucket",
        "what": "Object storage bucket. Stores files, backups, static websites, and Terraform state.",
        "key_args": ["bucket", "force_destroy", "tags"],
        "cost_note": "Charged per GB stored and per request. First 5 GB/month free.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket",
    },
    "aws_security_group": {
        "title": "Security Group",
        "what": "A stateful firewall controlling inbound and outbound traffic for AWS resources.",
        "key_args": ["name", "vpc_id", "ingress", "egress"],
        "cost_note": "Security groups are free.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group",
    },
    "aws_iam_role": {
        "title": "IAM Role",
        "what": "An AWS identity with permissions policies, assumed by services like EC2 or Lambda.",
        "key_args": ["name", "assume_role_policy", "tags"],
        "cost_note": "IAM roles are free.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role",
    },
    "aws_iam_policy": {
        "title": "IAM Policy",
        "what": "A JSON document granting or denying specific AWS API actions on specific resources.",
        "key_args": ["name", "policy"],
        "cost_note": "IAM policies are free.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy",
    },
    "aws_lambda_function": {
        "title": "Lambda Function",
        "what": "Serverless function that runs code in response to events without managing servers.",
        "key_args": ["function_name", "runtime", "handler", "role", "filename"],
        "cost_note": "First 1M requests/month free. Billed per 1ms of execution thereafter.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function",
    },
    "aws_db_instance": {
        "title": "RDS Database Instance",
        "what": "A managed relational database (MySQL, PostgreSQL, etc.) running on AWS RDS.",
        "key_args": ["identifier", "engine", "instance_class", "allocated_storage", "username", "password"],
        "cost_note": "Billed per hour by instance class. db.t3.micro is free-tier eligible.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_instance",
    },
    "aws_cloudfront_distribution": {
        "title": "CloudFront Distribution",
        "what": "A CDN that caches and serves content from edge locations worldwide.",
        "key_args": ["origin", "enabled", "default_cache_behavior", "aliases"],
        "cost_note": "First 1 TB/month and 10M requests free. Charges apply beyond that.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_distribution",
    },
    "aws_route53_record": {
        "title": "Route 53 DNS Record",
        "what": "A DNS record (A, CNAME, MX, etc.) in an AWS Route 53 hosted zone.",
        "key_args": ["zone_id", "name", "type", "ttl", "records"],
        "cost_note": "$0.50/hosted zone/month + $0.40 per 1M queries.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_record",
    },
    "aws_internet_gateway": {
        "title": "Internet Gateway",
        "what": "Attaches to a VPC to allow traffic between the VPC and the public internet.",
        "key_args": ["vpc_id", "tags"],
        "cost_note": "Internet gateways are free; data transfer charges apply.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/internet_gateway",
    },
    "aws_lb": {
        "title": "Application/Network Load Balancer",
        "what": "Distributes incoming traffic across multiple targets (EC2, containers, IPs).",
        "key_args": ["name", "internal", "load_balancer_type", "subnets", "security_groups"],
        "cost_note": "~$16/month base charge + per LCU consumed.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb",
    },
    "aws_ecs_service": {
        "title": "ECS Service",
        "what": "Runs and maintains a desired count of ECS task definitions as long-running services.",
        "key_args": ["name", "cluster", "task_definition", "desired_count", "launch_type"],
        "cost_note": "ECS itself is free; billed for underlying EC2 or Fargate compute.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_service",
    },
    "aws_eks_cluster": {
        "title": "EKS Cluster",
        "what": "A managed Kubernetes control plane on AWS.",
        "key_args": ["name", "role_arn", "version", "vpc_config"],
        "cost_note": "$0.10/hour per cluster (~$73/month). Worker nodes billed separately.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster",
    },
    "aws_elastic_beanstalk_environment": {
        "title": "Elastic Beanstalk Environment",
        "what": "A managed platform-as-a-service environment for deploying web applications.",
        "key_args": ["name", "application", "solution_stack_name", "tier"],
        "cost_note": "No charge for Beanstalk itself; billed for underlying EC2, ELB, etc.",
        "docs": "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elastic_beanstalk_environment",
    },
    "proxmox_vm_qemu": {
        "title": "Proxmox QEMU Virtual Machine",
        "what": "A KVM/QEMU virtual machine managed by a Proxmox hypervisor.",
        "key_args": ["name", "target_node", "clone", "cores", "memory", "disk", "network"],
        "cost_note": "On-premises resource — no cloud charges.",
        "docs": "https://registry.terraform.io/providers/Telmate/proxmox/latest/docs/resources/vm_qemu",
    },
    "proxmox_lxc": {
        "title": "Proxmox LXC Container",
        "what": "A lightweight Linux container managed by a Proxmox hypervisor.",
        "key_args": ["hostname", "target_node", "ostemplate", "cores", "memory", "rootfs"],
        "cost_note": "On-premises resource — no cloud charges.",
        "docs": "https://registry.terraform.io/providers/Telmate/proxmox/latest/docs/resources/lxc",
    },
    "random_id": {
        "title": "Random ID",
        "what": "Generates a random byte string useful for unique resource naming.",
        "key_args": ["byte_length", "keepers"],
        "cost_note": "Free — local computation only.",
        "docs": "https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/id",
    },
    "null_resource": {
        "title": "Null Resource",
        "what": "A placeholder resource with no real infrastructure, used to trigger provisioners.",
        "key_args": ["triggers"],
        "cost_note": "Free — no real infrastructure created.",
        "docs": "https://registry.terraform.io/providers/hashicorp/null/latest/docs/resources/resource",
    },
}

# Actions that permanently remove or recreate infrastructure
DESTRUCTIVE_ACTIONS: frozenset[str] = frozenset({"delete", "replace"})

# Human-readable labels for plan change actions
ACTION_LABELS: dict[str, str] = {
    "create":  "will be created",
    "update":  "will be updated in-place",
    "delete":  "will be DESTROYED",
    "replace": "will be DESTROYED and re-created",
    "no-op":   "is unchanged",
    "read":    "will be read (data source)",
}

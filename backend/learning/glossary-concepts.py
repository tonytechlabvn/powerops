"""Static dictionary of all Terraform concept definitions.

Imported by glossary.py — do not import this module directly.
Each concept has: term, one_line, explanation, example (HCL), related_concepts.
"""
from __future__ import annotations

CONCEPTS: dict[str, dict] = {
    "state": {
        "term": "state",
        "one_line": "Terraform's record of what infrastructure it manages.",
        "explanation": (
            "Terraform stores a snapshot of every resource it has created in a "
            "state file (terraform.tfstate). On each plan/apply run it compares "
            "your configuration against this state to determine what changes are "
            "needed. Without state, Terraform cannot track existing resources or "
            "detect drift between your config and reality."
        ),
        "example": (
            '# State is managed automatically. To inspect it:\n'
            'terraform show\n'
            'terraform state list\n'
            'terraform state show aws_instance.web'
        ),
        "related_concepts": ["backend", "plan", "apply", "workspace"],
    },
    "plan": {
        "term": "plan",
        "one_line": "A dry-run that shows what Terraform will change before touching anything.",
        "explanation": (
            "'terraform plan' reads your .tf files, compares them to the current "
            "state, and prints a diff. Green '+' lines are additions, red '-' "
            "lines are deletions, yellow '~' lines are in-place updates. No "
            "infrastructure is modified during a plan — it is always safe to run."
        ),
        "example": (
            'terraform plan\n'
            'terraform plan -out=tfplan       # save plan to file\n'
            'terraform plan -var="env=prod"   # pass variable inline'
        ),
        "related_concepts": ["apply", "state", "variable"],
    },
    "apply": {
        "term": "apply",
        "one_line": "Execute a plan and make real infrastructure changes.",
        "explanation": (
            "'terraform apply' carries out the changes shown in a plan. By default "
            "it runs a fresh plan and asks for confirmation before proceeding. You "
            "can pass a saved plan file to apply exactly those changes without "
            "re-planning. Apply updates the state file after each successful "
            "resource operation."
        ),
        "example": (
            'terraform apply                  # plan + prompt + apply\n'
            'terraform apply tfplan           # apply a saved plan file\n'
            'terraform apply -auto-approve    # skip confirmation prompt'
        ),
        "related_concepts": ["plan", "destroy", "state"],
    },
    "destroy": {
        "term": "destroy",
        "one_line": "Remove all infrastructure managed by the current configuration.",
        "explanation": (
            "'terraform destroy' is shorthand for 'terraform apply -destroy'. It "
            "generates a plan that deletes every resource tracked in state and "
            "asks for confirmation. Use it to tear down environments cleanly. "
            "Individual resources can be removed with 'terraform destroy -target'."
        ),
        "example": (
            'terraform destroy                        # destroy everything\n'
            'terraform destroy -target aws_instance.web  # destroy one resource'
        ),
        "related_concepts": ["apply", "state", "lifecycle"],
    },
    "provider": {
        "term": "provider",
        "one_line": "A plugin that lets Terraform talk to a specific platform (AWS, Azure, etc.).",
        "explanation": (
            "Providers are Go plugins distributed via the Terraform Registry. Each "
            "provider implements CRUD operations for a platform's API — AWS, Azure, "
            "GCP, Proxmox, Kubernetes, and hundreds more. You declare required "
            "providers in a 'terraform' block and configure credentials in a "
            "'provider' block. Terraform downloads providers automatically on init."
        ),
        "example": (
            'terraform {\n'
            '  required_providers {\n'
            '    aws = {\n'
            '      source  = "hashicorp/aws"\n'
            '      version = "~> 5.0"\n'
            '    }\n'
            '  }\n'
            '}\n\n'
            'provider "aws" {\n'
            '  region = "us-east-1"\n'
            '}'
        ),
        "related_concepts": ["required_providers", "terraform block", "resource"],
    },
    "resource": {
        "term": "resource",
        "one_line": "A single infrastructure object managed by Terraform.",
        "explanation": (
            "Resource blocks are the core of Terraform configuration. Each block "
            "declares one infrastructure object: its type (from the provider), a "
            "local name, and its configuration arguments. Terraform maps each "
            "resource block to a real API object and tracks it in state."
        ),
        "example": (
            'resource "aws_instance" "web" {\n'
            '  ami           = "ami-0c55b159cbfafe1f0"\n'
            '  instance_type = "t3.micro"\n\n'
            '  tags = {\n'
            '    Name = "web-server"\n'
            '  }\n'
            '}'
        ),
        "related_concepts": ["provider", "data source", "depends_on", "lifecycle"],
    },
    "data source": {
        "term": "data source",
        "one_line": "Read-only lookup of existing infrastructure not managed by Terraform.",
        "explanation": (
            "Data sources let you query information from your provider without "
            "creating or modifying resources. Common uses: look up the latest AMI "
            "ID, fetch an existing VPC's ID, or read a secret from AWS Secrets "
            "Manager. Data source results are available as attributes to reference "
            "in resource blocks."
        ),
        "example": (
            'data "aws_ami" "ubuntu" {\n'
            '  most_recent = true\n'
            '  owners      = ["099720109477"]\n\n'
            '  filter {\n'
            '    name   = "name"\n'
            '    values = ["ubuntu/images/hvm-ssd/ubuntu-*-22.04-amd64-*"]\n'
            '  }\n'
            '}\n\n'
            'resource "aws_instance" "web" {\n'
            '  ami = data.aws_ami.ubuntu.id\n'
            '}'
        ),
        "related_concepts": ["resource", "provider", "locals"],
    },
    "variable": {
        "term": "variable",
        "one_line": "A parameter that makes your configuration reusable and environment-agnostic.",
        "explanation": (
            "Input variables (declared with 'variable' blocks) allow callers to "
            "pass values into a module or root configuration. They support type "
            "constraints, default values, validation rules, and sensitivity flags. "
            "Values can be supplied via CLI flags, .tfvars files, or environment "
            "variables prefixed with TF_VAR_."
        ),
        "example": (
            'variable "instance_type" {\n'
            '  type        = string\n'
            '  description = "EC2 instance size"\n'
            '  default     = "t3.micro"\n'
            '}\n\n'
            'resource "aws_instance" "web" {\n'
            '  instance_type = var.instance_type\n'
            '}'
        ),
        "related_concepts": ["output", "locals", "module"],
    },
    "output": {
        "term": "output",
        "one_line": "A value exported from your configuration after apply.",
        "explanation": (
            "Output values are like return values for a Terraform module. They are "
            "printed to the terminal after a successful apply and can be queried "
            "with 'terraform output'. Parent modules can read child module outputs "
            "via 'module.<name>.<output_name>'. Outputs marked sensitive are "
            "redacted from terminal display."
        ),
        "example": (
            'output "instance_public_ip" {\n'
            '  description = "Public IP of the web server"\n'
            '  value       = aws_instance.web.public_ip\n'
            '}\n\n'
            '# Query after apply:\n'
            'terraform output instance_public_ip'
        ),
        "related_concepts": ["variable", "module", "locals"],
    },
    "module": {
        "term": "module",
        "one_line": "A reusable package of Terraform configuration files.",
        "explanation": (
            "Modules let you encapsulate and reuse infrastructure patterns. The "
            "root module is your working directory. Child modules are called with "
            "'module' blocks and can come from the local filesystem, the Terraform "
            "Registry, or git repositories. Modules accept input variables and "
            "export outputs, making them composable building blocks."
        ),
        "example": (
            'module "vpc" {\n'
            '  source  = "terraform-aws-modules/vpc/aws"\n'
            '  version = "~> 5.0"\n\n'
            '  name = "my-vpc"\n'
            '  cidr = "10.0.0.0/16"\n'
            '}'
        ),
        "related_concepts": ["variable", "output", "required_providers"],
    },
    "workspace": {
        "term": "workspace",
        "one_line": "An isolated state environment within a single configuration.",
        "explanation": (
            "Workspaces allow you to maintain separate state files for the same "
            "configuration — useful for dev/staging/prod environments. The default "
            "workspace is named 'default'. The current workspace name is available "
            "as 'terraform.workspace' for use in expressions."
        ),
        "example": (
            'terraform workspace new staging\n'
            'terraform workspace select staging\n'
            'terraform workspace list\n\n'
            'resource "aws_instance" "web" {\n'
            '  tags = { Env = terraform.workspace }\n'
            '}'
        ),
        "related_concepts": ["state", "backend", "variable"],
    },
    "backend": {
        "term": "backend",
        "one_line": "Where Terraform stores its state file (local disk, S3, Terraform Cloud, etc.).",
        "explanation": (
            "By default Terraform writes state to terraform.tfstate on your local "
            "disk. A remote backend stores state in a shared location so teams can "
            "collaborate safely. Remote backends also support state locking to "
            "prevent concurrent applies. Common backends: S3 + DynamoDB, "
            "Azure Blob, GCS, or Terraform Cloud/Enterprise."
        ),
        "example": (
            'terraform {\n'
            '  backend "s3" {\n'
            '    bucket         = "my-tf-state"\n'
            '    key            = "prod/terraform.tfstate"\n'
            '    region         = "us-east-1"\n'
            '    dynamodb_table = "tf-state-lock"\n'
            '    encrypt        = true\n'
            '  }\n'
            '}'
        ),
        "related_concepts": ["state", "workspace", "terraform block"],
    },
    "provisioner": {
        "term": "provisioner",
        "one_line": "A last-resort escape hatch that runs scripts on a resource after creation.",
        "explanation": (
            "Provisioners (remote-exec, local-exec, file) run scripts or commands "
            "after a resource is created or destroyed. HashiCorp considers them a "
            "last resort because they make plans non-deterministic and break "
            "idempotency. Prefer cloud-init, user_data, or configuration "
            "management tools over provisioners where possible."
        ),
        "example": (
            'resource "aws_instance" "web" {\n'
            '  # ...\n\n'
            '  provisioner "remote-exec" {\n'
            '    inline = [\n'
            '      "sudo apt-get update",\n'
            '      "sudo apt-get install -y nginx",\n'
            '    ]\n'
            '  }\n'
            '}'
        ),
        "related_concepts": ["resource", "lifecycle"],
    },
    "lifecycle": {
        "term": "lifecycle",
        "one_line": "Rules that control how Terraform creates, updates, and destroys a resource.",
        "explanation": (
            "The lifecycle meta-argument block lets you override default resource "
            "behaviour. Key settings: create_before_destroy avoids downtime on "
            "replacements; prevent_destroy blocks accidental deletion; "
            "ignore_changes tells Terraform to ignore drift on specific attributes; "
            "replace_triggered_by forces replacement when another resource changes."
        ),
        "example": (
            'resource "aws_instance" "web" {\n'
            '  # ...\n\n'
            '  lifecycle {\n'
            '    create_before_destroy = true\n'
            '    prevent_destroy       = true\n'
            '    ignore_changes        = [tags]\n'
            '  }\n'
            '}'
        ),
        "related_concepts": ["resource", "depends_on", "provisioner"],
    },
    "count": {
        "term": "count",
        "one_line": "Create N copies of a resource using a single block.",
        "explanation": (
            "The 'count' meta-argument accepts an integer and tells Terraform to "
            "create that many instances of the resource. Each instance is "
            "addressable as resource.name[index]. Use count.index to differentiate "
            "instances. For map/set iteration, prefer for_each."
        ),
        "example": (
            'resource "aws_instance" "worker" {\n'
            '  count         = 3\n'
            '  ami           = "ami-0c55b159cbfafe1f0"\n'
            '  instance_type = "t3.micro"\n\n'
            '  tags = { Name = "worker-${count.index}" }\n'
            '}'
        ),
        "related_concepts": ["for_each", "resource", "variable"],
    },
    "for_each": {
        "term": "for_each",
        "one_line": "Iterate over a map or set to create one resource instance per element.",
        "explanation": (
            "'for_each' accepts a map or set of strings and creates one resource "
            "instance per element. Each instance key is available as 'each.key' "
            "and its value as 'each.value'. Unlike count, for_each instances have "
            "stable identity keyed by map key, so adding/removing one entry does "
            "not affect other instances."
        ),
        "example": (
            'variable "buckets" {\n'
            '  default = { logs = "us-east-1", backups = "us-west-2" }\n'
            '}\n\n'
            'resource "aws_s3_bucket" "this" {\n'
            '  for_each = var.buckets\n'
            '  bucket   = each.key\n'
            '}'
        ),
        "related_concepts": ["count", "resource", "variable"],
    },
    "depends_on": {
        "term": "depends_on",
        "one_line": "Explicitly declare that one resource must be created before another.",
        "explanation": (
            "Terraform automatically infers dependencies from attribute references. "
            "Use depends_on only when the dependency is not visible in the "
            "configuration — for example, when an IAM policy must exist before a "
            "Lambda can be invoked even though the Lambda resource does not "
            "directly reference the policy ARN."
        ),
        "example": (
            'resource "aws_iam_role_policy_attachment" "attach" {\n'
            '  # ...\n'
            '}\n\n'
            'resource "aws_lambda_function" "fn" {\n'
            '  # ...\n'
            '  depends_on = [aws_iam_role_policy_attachment.attach]\n'
            '}'
        ),
        "related_concepts": ["resource", "lifecycle", "module"],
    },
    "locals": {
        "term": "locals",
        "one_line": "Named expressions that reduce repetition within a module.",
        "explanation": (
            "Local values (declared in a 'locals' block) assign a name to an "
            "expression so it can be reused without repeating the logic. They are "
            "computed once and are not exposed as outputs or inputs. Use them to "
            "centralise repeated expressions like environment-based name prefixes."
        ),
        "example": (
            'locals {\n'
            '  env         = terraform.workspace\n'
            '  name_prefix = "${var.project}-${local.env}"\n'
            '  common_tags = {\n'
            '    Project     = var.project\n'
            '    Environment = local.env\n'
            '    ManagedBy   = "terraform"\n'
            '  }\n'
            '}'
        ),
        "related_concepts": ["variable", "output", "data source"],
    },
    "terraform block": {
        "term": "terraform block",
        "one_line": "Top-level block that configures Terraform itself — version, backend, providers.",
        "explanation": (
            "The 'terraform' block configures Terraform's own behaviour. It is "
            "the place to pin the required Terraform CLI version, declare required "
            "providers with their source and version constraints, and configure the "
            "state backend. There can only be one terraform block per module."
        ),
        "example": (
            'terraform {\n'
            '  required_version = ">= 1.5.0"\n\n'
            '  required_providers {\n'
            '    aws = {\n'
            '      source  = "hashicorp/aws"\n'
            '      version = "~> 5.0"\n'
            '    }\n'
            '  }\n\n'
            '  backend "s3" {\n'
            '    bucket = "my-tf-state"\n'
            '    key    = "terraform.tfstate"\n'
            '    region = "us-east-1"\n'
            '  }\n'
            '}'
        ),
        "related_concepts": ["provider", "backend", "required_providers"],
    },
    "required_providers": {
        "term": "required_providers",
        "one_line": "Declares which providers your module needs and pins their versions.",
        "explanation": (
            "The required_providers block inside a terraform block lists every "
            "provider the module uses, with its registry source address and a "
            "version constraint. Terraform downloads matching providers during "
            "'terraform init'. Pinning versions prevents unexpected breakage when "
            "provider updates introduce breaking changes."
        ),
        "example": (
            'terraform {\n'
            '  required_providers {\n'
            '    aws = {\n'
            '      source  = "hashicorp/aws"\n'
            '      version = "~> 5.0"\n'
            '    }\n'
            '    random = {\n'
            '      source  = "hashicorp/random"\n'
            '      version = ">= 3.1"\n'
            '    }\n'
            '  }\n'
            '}'
        ),
        "related_concepts": ["terraform block", "provider", "module"],
    },
}

# Ordered list of all concept names for iteration
CONCEPT_NAMES: list[str] = list(CONCEPTS.keys())

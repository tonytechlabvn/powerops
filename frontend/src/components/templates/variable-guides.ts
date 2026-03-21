// Beginner-friendly guides for common Terraform template variables.
// Each guide explains what the variable is, how to find the value, and gives clickable examples.

export interface VariableGuide {
  title: string
  explanation: string
  howToFind?: string
  examples?: string[]
  warning?: string
}

export const VARIABLE_GUIDES: Record<string, VariableGuide> = {
  // --- AWS Common ---
  aws_region: {
    title: 'AWS Region',
    explanation: 'The geographic location where your resources will be created. Choose a region close to your users for lower latency.',
    howToFind: 'Go to AWS Console → top-right dropdown shows your current region. Common choices: us-east-1 (Virginia), ap-southeast-1 (Singapore).',
    examples: ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'],
  },
  instance_type: {
    title: 'EC2 Instance Size',
    explanation: 'Determines how much CPU and RAM your virtual machine gets. t3.micro is free-tier eligible and good for testing. t3.small for light workloads.',
    howToFind: 'AWS Console → EC2 → Instance Types. For testing, use t3.micro (free tier). For production, t3.medium or larger.',
    examples: ['t3.micro', 't3.small', 't3.medium', 't3.large'],
    warning: 'Larger instances cost more. t3.micro is free for 750 hours/month in the first year.',
  },
  ami_id: {
    title: 'Amazon Machine Image (AMI)',
    explanation: 'The operating system image for your VM. Think of it like choosing Windows or Ubuntu when installing an OS. Each region has different AMI IDs.',
    howToFind: 'AWS Console → EC2 → AMIs → search "ubuntu" or "amazon linux". Copy the AMI ID (starts with ami-). Make sure it matches your region!',
    examples: ['ami-0c02fb55956c7d316', 'ami-0557a15b87f6559cf'],
    warning: 'AMI IDs are region-specific. An AMI from us-east-1 won\'t work in eu-west-1.',
  },
  key_name: {
    title: 'SSH Key Pair Name',
    explanation: 'The name of your SSH key pair in AWS — this lets you log into the server via SSH. You must create this in AWS first.',
    howToFind: 'AWS Console → EC2 → Key Pairs → Create Key Pair. Give it a name and download the .pem file. Enter that name here.',
    examples: ['my-key', 'dev-key', 'production-key'],
    warning: 'Keep the downloaded .pem file safe — you cannot download it again! Without it you cannot SSH into your instance.',
  },
  instance_name: {
    title: 'Instance Name',
    explanation: 'A friendly name tag for your VM. This appears in the AWS Console so you can identify it easily. Use something descriptive.',
    examples: ['web-server', 'api-backend', 'test-instance'],
  },
  allowed_ssh_cidr: {
    title: 'SSH Access IP Range',
    explanation: 'Which IP addresses can SSH into your server. 0.0.0.0/0 means anyone — this is insecure! Use your own IP for safety.',
    howToFind: 'Google "what is my IP" to find your public IP, then add /32 at the end (e.g. 203.0.113.42/32). This restricts SSH to only your IP.',
    examples: ['0.0.0.0/0', '203.0.113.42/32', '10.0.0.0/8'],
    warning: 'Using 0.0.0.0/0 allows SSH from ANY IP. For production, always restrict to your IP!',
  },
  root_volume_size_gb: {
    title: 'Disk Size (GB)',
    explanation: 'How much storage (hard drive space) your server gets in gigabytes. 20GB is enough for most basic servers. Increase for data-heavy apps.',
    examples: ['20', '50', '100'],
  },
  environment: {
    title: 'Environment Tag',
    explanation: 'A label to organize resources. "dev" for development/testing, "staging" for pre-production, "prod" for live production.',
    examples: ['dev', 'staging', 'prod'],
  },

  // --- AWS VPC ---
  cidr_block: {
    title: 'VPC IP Range (CIDR)',
    explanation: 'The private IP address range for your virtual network. Think of it as the "address space" for all resources in this VPC. 10.0.0.0/16 gives you 65,536 IP addresses.',
    howToFind: 'Use the default 10.0.0.0/16 unless you need to connect multiple VPCs (then use different ranges like 10.1.0.0/16).',
    examples: ['10.0.0.0/16', '172.16.0.0/16', '192.168.0.0/16'],
  },
  vpc_name: {
    title: 'VPC Name',
    explanation: 'A friendly name for your Virtual Private Cloud network. Shows up in AWS Console.',
    examples: ['main', 'production', 'dev-vpc'],
  },
  vpc_id: {
    title: 'VPC ID',
    explanation: 'The unique identifier of an existing VPC where this resource will be created.',
    howToFind: 'AWS Console → VPC → Your VPCs. Copy the VPC ID (starts with vpc-). Or use the vpc-basic template to create one first.',
    examples: ['vpc-0a1b2c3d4e5f6g7h8'],
  },
  public_subnet_cidrs: {
    title: 'Public Subnet IP Ranges',
    explanation: 'IP ranges for subnets that can be reached from the internet (for web servers, load balancers). Comma-separated, one per availability zone.',
    examples: ['10.0.1.0/24,10.0.2.0/24'],
  },
  private_subnet_cidrs: {
    title: 'Private Subnet IP Ranges',
    explanation: 'IP ranges for subnets hidden from the internet (for databases, internal services). Comma-separated.',
    examples: ['10.0.11.0/24,10.0.12.0/24'],
  },
  availability_zones: {
    title: 'Availability Zones',
    explanation: 'AWS data centers within a region. Using multiple AZs gives high availability — if one goes down, your app stays up.',
    howToFind: 'Each region has 2-6 AZs. For us-east-1: us-east-1a, us-east-1b, etc. Match the count to your subnet count.',
    examples: ['us-east-1a,us-east-1b', 'ap-southeast-1a,ap-southeast-1b'],
  },
  subnet_ids: {
    title: 'Subnet IDs',
    explanation: 'IDs of existing subnets where resources will be placed. Use private subnets for databases.',
    howToFind: 'AWS Console → VPC → Subnets. Copy subnet IDs (start with subnet-). Or deploy vpc-basic template first.',
    examples: ['subnet-abc123,subnet-def456'],
  },

  // --- AWS S3 ---
  bucket_name: {
    title: 'S3 Bucket Name',
    explanation: 'A globally unique name for your storage bucket. Must be unique across ALL AWS accounts worldwide. Use lowercase letters, numbers, and hyphens only.',
    examples: ['my-company-website-2024', 'app-assets-prod'],
    warning: 'Bucket names are globally unique. If someone else has the name, you cannot use it. Try adding your company name or random suffix.',
  },
  index_document: {
    title: 'Index Page',
    explanation: 'The default page shown when someone visits your website (like the homepage).',
    examples: ['index.html'],
  },
  error_document: {
    title: 'Error Page',
    explanation: 'The page shown when someone visits a URL that doesn\'t exist (404 error page).',
    examples: ['error.html', '404.html'],
  },

  // --- AWS RDS ---
  instance_class: {
    title: 'Database Instance Size',
    explanation: 'Determines CPU and RAM for your database. db.t3.micro is free-tier eligible and good for development.',
    examples: ['db.t3.micro', 'db.t3.small', 'db.t3.medium'],
    warning: 'db.t3.micro is free for 750 hours/month in the first year. Larger instances can cost $50-500+/month.',
  },
  db_name: {
    title: 'Database Name',
    explanation: 'The name of the initial database created inside the RDS instance. Your app will connect to this database.',
    examples: ['appdb', 'myapp_production', 'webapp'],
  },
  username: {
    title: 'Database Username',
    explanation: 'The master admin username for the database. Your app uses this to connect.',
    examples: ['dbadmin', 'admin', 'appuser'],
    warning: 'Don\'t use "admin" or "root" in production — use a unique username for security.',
  },
  allocated_storage: {
    title: 'Storage Size (GB)',
    explanation: 'How much disk space the database gets. 20GB is minimum. Increase based on expected data size.',
    examples: ['20', '50', '100'],
  },

  // --- AWS Security Group ---
  name_prefix: {
    title: 'Name Prefix',
    explanation: 'A prefix added to resource names for easy identification in AWS Console.',
    examples: ['web', 'api', 'app'],
  },
  allowed_ssh_cidrs: {
    title: 'SSH Access IP Ranges',
    explanation: 'Comma-separated IP ranges allowed to SSH. Use your own IP for security.',
    howToFind: 'Google "what is my IP", then add /32 (e.g. 203.0.113.42/32).',
    examples: ['0.0.0.0/0', '203.0.113.42/32'],
    warning: '0.0.0.0/0 allows SSH from anywhere — only use for testing!',
  },

  // --- Proxmox Common ---
  proxmox_api_url: {
    title: 'Proxmox API URL',
    explanation: 'The URL to your Proxmox server\'s API. Usually your Proxmox web UI URL with /api2/json appended.',
    howToFind: 'If you access Proxmox at https://192.168.1.100:8006, the API URL is https://192.168.1.100:8006/api2/json',
    examples: ['https://192.168.1.100:8006/api2/json', 'https://proxmox.local:8006/api2/json'],
  },
  proxmox_node: {
    title: 'Proxmox Node',
    explanation: 'The name of your Proxmox server node. This is the hostname shown in the Proxmox sidebar.',
    howToFind: 'Proxmox Web UI → left sidebar → Datacenter → your node name is listed there (usually "pve" by default).',
    examples: ['pve', 'proxmox1', 'node1'],
  },
  vmid: {
    title: 'VM/Container ID',
    explanation: 'A unique numeric ID for the VM or container in Proxmox. Each VM/container must have a different ID (100-999999).',
    howToFind: 'Proxmox Web UI → check existing VM IDs in the sidebar. Pick an unused number.',
    examples: ['200', '300', '400'],
    warning: 'If this ID is already used by another VM/container, the deployment will fail.',
  },
  vm_name: {
    title: 'VM Name',
    explanation: 'A friendly hostname for the virtual machine. Shows up in Proxmox UI and is set as the VM\'s hostname.',
    examples: ['ubuntu-vm', 'web-server', 'dev-machine'],
  },
  hostname: {
    title: 'Container Hostname',
    explanation: 'The hostname for the LXC container. This is what appears when you log into the container.',
    examples: ['web-container', 'app-01', 'dev-ct'],
  },
  template_name: {
    title: 'VM Template Name',
    explanation: 'The name of a Proxmox VM template to clone from. You need to create a cloud-init template first.',
    howToFind: 'Proxmox Web UI → select your node → look for templates (usually marked with a special icon). Common: ubuntu-22.04-cloudinit.',
    examples: ['ubuntu-22.04-cloudinit', 'ubuntu-24.04-cloudinit', 'debian-12-cloudinit'],
  },
  ostemplate: {
    title: 'LXC OS Template',
    explanation: 'The OS template file for the LXC container. These are downloaded from Proxmox template storage.',
    howToFind: 'Proxmox UI → your node → local storage → CT Templates → Templates button to download. Copy the full path.',
    examples: ['local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst'],
  },
  cores: {
    title: 'CPU Cores',
    explanation: 'Number of virtual CPU cores assigned to the VM/container. 1-2 for testing, 4+ for production workloads.',
    examples: ['1', '2', '4'],
  },
  memory: {
    title: 'Memory (MB)',
    explanation: 'RAM in megabytes. 512MB for lightweight containers, 2048MB (2GB) for small servers, 4096MB+ for production.',
    examples: ['512', '1024', '2048', '4096'],
  },
  memory_mb: {
    title: 'Memory (MB)',
    explanation: 'RAM in megabytes. 2048MB = 2GB. For a basic web server, 2048MB is usually sufficient.',
    examples: ['1024', '2048', '4096'],
  },
  disk_size: {
    title: 'Disk Size (GB)',
    explanation: 'Storage space for the VM in gigabytes. 20GB for basic OS + apps, increase for data storage.',
    examples: ['20', '50', '100'],
  },
  disk_size_gb: {
    title: 'Disk Size (GB)',
    explanation: 'Storage space in gigabytes. 20GB minimum for Ubuntu with basic apps.',
    examples: ['20', '50', '100'],
  },
  ip_config: {
    title: 'Network IP Configuration',
    explanation: 'How the VM/container gets its IP address. "ip=dhcp" for automatic assignment, or set a static IP.',
    howToFind: 'Use "ip=dhcp" for automatic. For static: check your network range (e.g. 192.168.1.x) and pick an unused IP.',
    examples: ['ip=dhcp', 'ip=192.168.1.200/24,gw=192.168.1.1'],
  },
  ip_address: {
    title: 'IP Address',
    explanation: 'Static IP or "dhcp" for automatic. For static, use CIDR notation (IP/prefix).',
    examples: ['dhcp', '192.168.1.100/24'],
  },
  ip_config_base: {
    title: 'Base IP for Cluster',
    explanation: 'Starting IP for sequential VM assignment. Each VM gets base+index. Use "dhcp" for automatic.',
    examples: ['dhcp', '192.168.1.10'],
  },
  gateway: {
    title: 'Default Gateway',
    explanation: 'Your network\'s router IP. Required for static IP configs to allow internet access.',
    howToFind: 'Usually your router\'s IP — often 192.168.1.1 or 10.0.0.1. Check your network settings.',
    examples: ['192.168.1.1', '10.0.0.1'],
  },
  bridge: {
    title: 'Network Bridge',
    explanation: 'The Proxmox network bridge to connect to. vmbr0 is the default bridge on most Proxmox installs.',
    howToFind: 'Proxmox UI → your node → System → Network. The bridge name is listed there.',
    examples: ['vmbr0', 'vmbr1'],
  },
  ssh_public_key: {
    title: 'SSH Public Key',
    explanation: 'Your SSH public key for passwordless login. This is the CONTENT of your .pub file, not the filename.',
    howToFind: 'Run "cat ~/.ssh/id_rsa.pub" in your terminal. Copy the entire output starting with "ssh-rsa" or "ssh-ed25519".',
    examples: ['ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...'],
    warning: 'Paste the PUBLIC key (.pub file), never your private key!',
  },
  vm_count: {
    title: 'Number of VMs',
    explanation: 'How many identical VMs to create in the cluster. Each gets a sequential ID and IP.',
    examples: ['2', '3', '5'],
  },
  vmid_base: {
    title: 'Starting VM ID',
    explanation: 'The first VM ID in the cluster. VMs get IDs: base, base+1, base+2, etc.',
    examples: ['400', '500', '600'],
  },

  // --- General ---
  enable_nat_gateway: {
    title: 'NAT Gateway',
    explanation: 'Lets private subnets access the internet (for updates, API calls) without being publicly accessible. Costs ~$32/month.',
    warning: 'NAT Gateway costs ~$32/month + data transfer charges. Disable for development to save costs.',
  },
  versioning_enabled: {
    title: 'S3 Versioning',
    explanation: 'Keeps all versions of every file. If you accidentally delete or overwrite a file, you can recover old versions.',
  },
  multi_az: {
    title: 'Multi-AZ Deployment',
    explanation: 'Creates a standby database in another data center. If the primary fails, it auto-switches. Doubles the cost.',
    warning: 'Multi-AZ doubles database cost. Only enable for production workloads that need high availability.',
  },
  backup_retention_days: {
    title: 'Backup Retention (Days)',
    explanation: 'How many days to keep automated database backups. 7 days is a good default. Set to 0 to disable (not recommended).',
    examples: ['7', '14', '30'],
  },
}

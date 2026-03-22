// Shared field renderer for wizard step components.
// Each step defines a list of fields; this renders them consistently.

interface FieldDef {
  name: string
  label: string
  type: 'text' | 'number' | 'select'
  options?: string[]
  placeholder?: string
}

interface WizardStepFieldsProps {
  fields: FieldDef[]
  data: Record<string, unknown>
  defaults: Record<string, unknown>
  onChange: (data: Record<string, unknown>) => void
  description?: string
}

export function WizardStepFields({ fields, data, defaults, onChange, description }: WizardStepFieldsProps) {
  const getValue = (name: string) => {
    const val = data[name] ?? defaults[name] ?? ''
    return String(val)
  }

  const handleChange = (name: string, value: string, type: string) => {
    const parsed = type === 'number' ? (value === '' ? '' : Number(value)) : value
    onChange({ ...data, [name]: parsed })
  }

  return (
    <div className="space-y-3">
      {description && <p className="text-zinc-400 text-xs">{description}</p>}
      {fields.map(f => (
        <div key={f.name}>
          <label className="text-zinc-400 text-xs font-medium block mb-1">{f.label}</label>
          {f.type === 'select' && f.options ? (
            <select
              value={getValue(f.name)}
              onChange={e => handleChange(f.name, e.target.value, f.type)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2
                         text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
            >
              {f.options.map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          ) : (
            <input
              type={f.type}
              value={getValue(f.name)}
              onChange={e => handleChange(f.name, e.target.value, f.type)}
              placeholder={f.placeholder}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2
                         text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
            />
          )}
        </div>
      ))}
    </div>
  )
}

// ---- Step-specific field definitions ----

export const COMPUTE_FIELDS: FieldDef[] = [
  { name: 'instance_type', label: 'Instance Type', type: 'text', placeholder: 't3.micro' },
  { name: 'ami_id', label: 'AMI ID', type: 'text', placeholder: 'ami-0c02fb55956c7d316' },
  { name: 'cores', label: 'CPU Cores', type: 'number' },
  { name: 'memory_mb', label: 'Memory (MB)', type: 'number' },
]

export const NETWORKING_FIELDS: FieldDef[] = [
  { name: 'vpc_cidr', label: 'VPC CIDR', type: 'text', placeholder: '10.0.0.0/16' },
  { name: 'subnet_cidr', label: 'Subnet CIDR', type: 'text', placeholder: '10.0.1.0/24' },
  { name: 'availability_zone', label: 'Availability Zone', type: 'text', placeholder: 'us-east-1a' },
  { name: 'enable_nat_gateway', label: 'NAT Gateway', type: 'select', options: ['true', 'false'] },
]

export const STORAGE_FIELDS: FieldDef[] = [
  { name: 'volume_size_gb', label: 'Volume Size (GB)', type: 'number' },
  { name: 'storage_type', label: 'Storage Type', type: 'select', options: ['gp3', 'gp2', 'io1', 'standard'] },
  { name: 'bucket_name', label: 'S3 Bucket Name', type: 'text', placeholder: 'my-bucket' },
]

export const SECURITY_FIELDS: FieldDef[] = [
  { name: 'allowed_ssh_cidr', label: 'Allowed SSH CIDR', type: 'text', placeholder: '0.0.0.0/0' },
  { name: 'enable_encryption', label: 'Enable Encryption', type: 'select', options: ['true', 'false'] },
  { name: 'iam_role_name', label: 'IAM Role Name', type: 'text', placeholder: 'ec2-instance-role' },
]

export const CONNECTIVITY_FIELDS: FieldDef[] = [
  { name: 'vpn_type', label: 'VPN Type', type: 'select', options: ['wireguard', 'ipsec', 'openvpn'] },
  { name: 'tunnel_cidr', label: 'Tunnel CIDR', type: 'text', placeholder: '10.100.0.0/24' },
  { name: 'listen_port', label: 'Listen Port', type: 'number' },
]

export const MONITORING_FIELDS: FieldDef[] = [
  { name: 'enable_cloudwatch', label: 'CloudWatch', type: 'select', options: ['true', 'false'] },
  { name: 'alarm_email', label: 'Alarm Email', type: 'text', placeholder: 'ops@example.com' },
  { name: 'log_retention_days', label: 'Log Retention (days)', type: 'number' },
]

// Custom React Flow node components for all resource types.
// Each node is memoized and uses consistent Handle placement.

import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'

// Shared node wrapper with provider-specific border color
function NodeShell({ children, selected, color }: { children: React.ReactNode; selected?: boolean; color: string }) {
  return (
    <div className={`px-3 py-2 rounded-lg border-2 min-w-[140px] bg-zinc-800
      ${selected ? 'border-blue-400 shadow-lg shadow-blue-500/20' : `border-${color}`}`}>
      <Handle type="target" position={Position.Top} className="!bg-zinc-400" />
      {children}
      <Handle type="source" position={Position.Bottom} className="!bg-zinc-400" />
    </div>
  )
}

// --- AWS Nodes (orange accent) ---

function EC2NodeInner({ data, selected }: NodeProps) {
  return (
    <NodeShell selected={selected} color="orange-600/50">
      <div className="flex items-center gap-2">
        <span className="text-orange-400 text-[10px] font-bold bg-orange-950 px-1.5 rounded">EC2</span>
        <span className="text-zinc-200 text-xs">{(data.label as string) || 'Instance'}</span>
      </div>
    </NodeShell>
  )
}
export const EC2Node = memo(EC2NodeInner)

function VPCNodeInner({ data, selected }: NodeProps) {
  return (
    <NodeShell selected={selected} color="orange-600/50">
      <div className="flex items-center gap-2">
        <span className="text-orange-400 text-[10px] font-bold bg-orange-950 px-1.5 rounded">VPC</span>
        <span className="text-zinc-200 text-xs">{(data.label as string) || 'Network'}</span>
      </div>
    </NodeShell>
  )
}
export const VPCNode = memo(VPCNodeInner)

function SecurityGroupNodeInner({ data, selected }: NodeProps) {
  return (
    <NodeShell selected={selected} color="orange-600/50">
      <div className="flex items-center gap-2">
        <span className="text-orange-400 text-[10px] font-bold bg-orange-950 px-1.5 rounded">SG</span>
        <span className="text-zinc-200 text-xs">{(data.label as string) || 'Security Group'}</span>
      </div>
    </NodeShell>
  )
}
export const SecurityGroupNode = memo(SecurityGroupNodeInner)

function S3NodeInner({ data, selected }: NodeProps) {
  return (
    <NodeShell selected={selected} color="orange-600/50">
      <div className="flex items-center gap-2">
        <span className="text-orange-400 text-[10px] font-bold bg-orange-950 px-1.5 rounded">S3</span>
        <span className="text-zinc-200 text-xs">{(data.label as string) || 'Bucket'}</span>
      </div>
    </NodeShell>
  )
}
export const S3Node = memo(S3NodeInner)

function RDSNodeInner({ data, selected }: NodeProps) {
  return (
    <NodeShell selected={selected} color="orange-600/50">
      <div className="flex items-center gap-2">
        <span className="text-orange-400 text-[10px] font-bold bg-orange-950 px-1.5 rounded">RDS</span>
        <span className="text-zinc-200 text-xs">{(data.label as string) || 'Database'}</span>
      </div>
    </NodeShell>
  )
}
export const RDSNode = memo(RDSNodeInner)

// --- Proxmox Nodes (green accent) ---

function ProxmoxVMNodeInner({ data, selected }: NodeProps) {
  return (
    <NodeShell selected={selected} color="green-600/50">
      <div className="flex items-center gap-2">
        <span className="text-green-400 text-[10px] font-bold bg-green-950 px-1.5 rounded">VM</span>
        <span className="text-zinc-200 text-xs">{(data.label as string) || 'QEMU VM'}</span>
      </div>
    </NodeShell>
  )
}
export const ProxmoxVMNode = memo(ProxmoxVMNodeInner)

function ProxmoxLXCNodeInner({ data, selected }: NodeProps) {
  return (
    <NodeShell selected={selected} color="green-600/50">
      <div className="flex items-center gap-2">
        <span className="text-green-400 text-[10px] font-bold bg-green-950 px-1.5 rounded">LXC</span>
        <span className="text-zinc-200 text-xs">{(data.label as string) || 'Container'}</span>
      </div>
    </NodeShell>
  )
}
export const ProxmoxLXCNode = memo(ProxmoxLXCNodeInner)

// --- Cross-provider Nodes (purple accent) ---

function VPNTunnelNodeInner({ data, selected }: NodeProps) {
  return (
    <NodeShell selected={selected} color="purple-600/50">
      <div className="flex items-center gap-2">
        <span className="text-purple-400 text-[10px] font-bold bg-purple-950 px-1.5 rounded">VPN</span>
        <span className="text-zinc-200 text-xs">{(data.label as string) || 'Tunnel'}</span>
      </div>
    </NodeShell>
  )
}
export const VPNTunnelNode = memo(VPNTunnelNodeInner)

// --- Provider Group (container subflow) ---

function ProviderGroupNodeInner({ data }: NodeProps) {
  return (
    <div className="p-3 min-w-[220px] min-h-[160px] rounded-xl border-2 border-dashed border-zinc-600 bg-zinc-900/30">
      <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
        {(data.label as string) || 'Provider'}
      </span>
    </div>
  )
}
export const ProviderGroupNode = memo(ProviderGroupNodeInner)

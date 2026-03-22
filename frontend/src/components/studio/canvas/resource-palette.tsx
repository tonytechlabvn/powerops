// Resource palette — draggable panel listing available resources by provider.
// Drag nodes from here onto the React Flow canvas.

import type { DragEvent } from 'react'

interface ResourceItem {
  type: string
  label: string
}

const RESOURCE_GROUPS: { provider: string; color: string; items: ResourceItem[] }[] = [
  {
    provider: 'AWS',
    color: 'text-orange-400',
    items: [
      { type: 'ec2Instance', label: 'EC2 Instance' },
      { type: 'vpcNetwork', label: 'VPC' },
      { type: 'securityGroup', label: 'Security Group' },
      { type: 's3Bucket', label: 'S3 Bucket' },
      { type: 'rdsInstance', label: 'RDS Instance' },
    ],
  },
  {
    provider: 'Proxmox',
    color: 'text-green-400',
    items: [
      { type: 'proxmoxVM', label: 'VM (QEMU)' },
      { type: 'proxmoxLXC', label: 'LXC Container' },
    ],
  },
  {
    provider: 'Cross-Provider',
    color: 'text-purple-400',
    items: [
      { type: 'vpnTunnel', label: 'VPN Tunnel' },
    ],
  },
  {
    provider: 'Groups',
    color: 'text-zinc-400',
    items: [
      { type: 'providerGroup', label: 'Provider Group' },
    ],
  },
]

function onDragStart(event: DragEvent, nodeType: string) {
  event.dataTransfer.setData('application/reactflow-nodetype', nodeType)
  event.dataTransfer.effectAllowed = 'move'
}

export function ResourcePalette() {
  return (
    <div className="w-48 shrink-0 border-r border-zinc-800 bg-zinc-900 overflow-y-auto p-3 space-y-4">
      <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">Resources</h3>
      {RESOURCE_GROUPS.map(group => (
        <div key={group.provider}>
          <h4 className={`text-[10px] font-bold uppercase tracking-wider mb-1.5 ${group.color}`}>
            {group.provider}
          </h4>
          <div className="space-y-1">
            {group.items.map(item => (
              <div
                key={item.type}
                draggable
                onDragStart={e => onDragStart(e, item.type)}
                className="px-2.5 py-1.5 bg-zinc-800 border border-zinc-700 rounded text-xs
                           text-zinc-300 cursor-grab hover:bg-zinc-700 hover:border-zinc-600
                           transition-colors active:cursor-grabbing"
              >
                {item.label}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

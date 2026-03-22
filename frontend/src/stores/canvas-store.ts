// Zustand store for React Flow canvas state — nodes, edges, and graph operations.

import { create } from 'zustand'
import {
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
} from '@xyflow/react'

// Expected variables per node type (for local preview)
const NODE_VARIABLES: Record<string, string[]> = {
  ec2Instance: ['instance_type', 'ami_id', 'instance_name'],
  vpcNetwork: ['vpc_cidr', 'enable_dns_hostnames'],
  securityGroup: ['allowed_ssh_cidr', 'allowed_ports'],
  s3Bucket: ['bucket_name', 'versioning_enabled'],
  rdsInstance: ['db_engine', 'db_instance_class', 'db_name'],
  proxmoxVM: ['proxmox_node', 'vm_id', 'cores', 'memory_mb'],
  proxmoxLXC: ['proxmox_node', 'lxc_id', 'cores', 'memory_mb'],
  vpnTunnel: ['tunnel_cidr', 'listen_port', 'vpn_type'],
}

export interface CanvasPreview {
  resourceCount: Record<string, number>
  expectedVariables: string[]
  warnings: string[]
}

interface CanvasStore {
  nodes: Node[]
  edges: Edge[]
  onNodesChange: OnNodesChange
  onEdgesChange: OnEdgesChange
  onConnect: OnConnect
  addNode: (type: string, position: { x: number; y: number }, parentId?: string) => void
  removeSelected: () => void
  toGraphJSON: () => { nodes: Node[]; edges: Edge[] }
  loadGraphJSON: (data: { nodes: Node[]; edges: Edge[] }) => void
  clearCanvas: () => void
  getPreview: () => CanvasPreview
}

export const useCanvasStore = create<CanvasStore>((set, get) => ({
  nodes: [],
  edges: [],

  onNodesChange: (changes) => set({ nodes: applyNodeChanges(changes, get().nodes) }),
  onEdgesChange: (changes) => set({ edges: applyEdgeChanges(changes, get().edges) }),
  onConnect: (connection) => set({ edges: addEdge(connection, get().edges) }),

  addNode: (type, position, parentId) => {
    const id = `${type}-${Date.now()}`
    const newNode: Node = {
      id,
      type,
      position,
      data: { label: type.replace(/([A-Z])/g, ' $1').trim() },
      parentId,
    }
    set({ nodes: [...get().nodes, newNode] })
  },

  removeSelected: () => set({
    nodes: get().nodes.filter(n => !n.selected),
    edges: get().edges.filter(e => !e.selected),
  }),

  toGraphJSON: () => ({ nodes: get().nodes, edges: get().edges }),

  loadGraphJSON: (data) => set({ nodes: data.nodes, edges: data.edges }),

  clearCanvas: () => set({ nodes: [], edges: [] }),

  getPreview: () => {
    const { nodes, edges } = get()
    // Count resources per type
    const resourceCount: Record<string, number> = {}
    const allVars = new Set<string>()

    for (const node of nodes) {
      if (node.type && node.type !== 'providerGroup') {
        resourceCount[node.type] = (resourceCount[node.type] ?? 0) + 1
        const vars = NODE_VARIABLES[node.type] ?? []
        vars.forEach(v => allVars.add(v))
      }
    }

    // Connection warnings
    const warnings: string[] = []
    const connectedNodeIds = new Set(edges.flatMap(e => [e.source, e.target]))
    const orphanedNodes = nodes.filter(n => n.type !== 'providerGroup' && !connectedNodeIds.has(n.id))
    if (orphanedNodes.length > 0) {
      warnings.push(`${orphanedNodes.length} node(s) not connected to any other resource`)
    }

    const vpnNodes = nodes.filter(n => n.type === 'vpnTunnel')
    for (const vpn of vpnNodes) {
      const vpnEdges = edges.filter(e => e.source === vpn.id || e.target === vpn.id)
      if (vpnEdges.length < 2) {
        warnings.push('VPN tunnel should connect two endpoints')
      }
    }

    return {
      resourceCount,
      expectedVariables: Array.from(allVars).sort(),
      warnings,
    }
  },
}))

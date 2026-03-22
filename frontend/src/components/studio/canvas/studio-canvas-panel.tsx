// Canvas mode panel — React Flow graph where users drag, connect, and generate templates.
// Full-width layout: resource palette | canvas | preview sidebar.

import { useCallback, useRef, type DragEvent } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type ReactFlowInstance,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { useCanvasStore } from '../../../stores/canvas-store'
import { ResourcePalette } from './resource-palette'
import { CanvasPreviewSidebar } from './canvas-preview-sidebar'
import {
  EC2Node,
  VPCNode,
  SecurityGroupNode,
  S3Node,
  RDSNode,
  ProxmoxVMNode,
  ProxmoxLXCNode,
  VPNTunnelNode,
  ProviderGroupNode,
} from './node-types/resource-nodes'

// CRITICAL: define outside component to prevent re-renders
const nodeTypes = {
  ec2Instance: EC2Node,
  vpcNetwork: VPCNode,
  securityGroup: SecurityGroupNode,
  s3Bucket: S3Node,
  rdsInstance: RDSNode,
  proxmoxVM: ProxmoxVMNode,
  proxmoxLXC: ProxmoxLXCNode,
  vpnTunnel: VPNTunnelNode,
  providerGroup: ProviderGroupNode,
}

interface StudioCanvasPanelProps {
  onGenerate: (description: string, providers: string[], complexity: string, context?: string) => void
  isGenerating: boolean
}

export function StudioCanvasPanel({ onGenerate, isGenerating }: StudioCanvasPanelProps) {
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect, addNode, toGraphJSON, removeSelected } =
    useCanvasStore()
  const reactFlowRef = useRef<ReactFlowInstance | null>(null)

  const handleDragOver = useCallback((event: DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const handleDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault()
      const nodeType = event.dataTransfer.getData('application/reactflow-nodetype')
      if (!nodeType || !reactFlowRef.current) return

      const position = reactFlowRef.current.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      })
      addNode(nodeType, position)
    },
    [addNode],
  )

  const handleGenerateFromCanvas = () => {
    const graphJSON = toGraphJSON()
    // Derive providers from node types present
    const providers = new Set<string>()
    for (const node of graphJSON.nodes) {
      if (node.type?.startsWith('ec2') || node.type?.startsWith('vpc') ||
          node.type?.startsWith('security') || node.type?.startsWith('s3') ||
          node.type?.startsWith('rds')) {
        providers.add('aws')
      }
      if (node.type?.startsWith('proxmox')) providers.add('proxmox')
    }
    const providerList = providers.size > 0 ? Array.from(providers) : ['aws']

    // Build description from graph
    const resourceSummary = graphJSON.nodes
      .filter(n => n.type !== 'providerGroup')
      .map(n => (n.data.label as string) || n.type)
      .join(', ')
    const description = `Generate a Jinja2 template with these resources: ${resourceSummary}`

    onGenerate(description, providerList, 'complex', JSON.stringify(graphJSON))
  }

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === 'Delete' || event.key === 'Backspace') {
        removeSelected()
      }
    },
    [removeSelected],
  )

  return (
    <div className="flex h-full" onKeyDown={handleKeyDown} tabIndex={0}>
      <ResourcePalette />
      <div className="flex-1 bg-zinc-950">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onInit={instance => { reactFlowRef.current = instance }}
          fitView
          className="bg-zinc-950"
        >
          <Background color="#333" gap={20} />
          <Controls className="!bg-zinc-800 !border-zinc-700 !rounded" />
          <MiniMap
            nodeColor="#3b82f6"
            maskColor="rgba(0,0,0,0.6)"
            className="!bg-zinc-900 !border-zinc-700"
          />
        </ReactFlow>
      </div>
      <CanvasPreviewSidebar onGenerate={handleGenerateFromCanvas} isGenerating={isGenerating} />
    </div>
  )
}

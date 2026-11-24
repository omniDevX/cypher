import { useState } from 'react'

type Connection = {
    relationshipType: string
    direction: 'incoming' | 'outgoing'
    relationshipProperties: Record<string, unknown>
    node: {
        labels: string[]
        idProperty: string
        id: string
        properties: Record<string, unknown>
    }
}

type Props = {
    nodeLabel: string
    idProperty: string
    nodeId: string
    displayName: string
    ancestorKeys?: string[]
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export default function RelationshipExplorer({
    nodeLabel,
    idProperty,
    nodeId,
    displayName,
    ancestorKeys = [],
}: Props) {
    const [expanded, setExpanded] = useState(false)
    const [connections, setConnections] = useState<Connection[]>([])
    const [loaded, setLoaded] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const nodeKey = `${nodeLabel}:${nodeId}`

    async function toggleConnections() {
        if (expanded) {
            setExpanded(false)
            return
        }

        if (!loaded) {
            setLoading(true)
            setError('')
            try {
                const path = [nodeLabel, idProperty, nodeId]
                    .map(encodeURIComponent)
                    .join('/')
                const response = await fetch(`${API_BASE}/loan/nodes/${path}/connections`)
                if (!response.ok) throw new Error(await response.text())
                setConnections(await response.json() as Connection[])
                setLoaded(true)
            } catch (cause) {
                setError(cause instanceof Error ? cause.message : String(cause))
                setLoading(false)
                return
            }
            setLoading(false)
        }

        setExpanded(true)
    }

    return (
        <div className="relationship-explorer">
            <button className="expand-connections" onClick={() => void toggleConnections()}>
                {loading ? 'Loading…' : expanded ? 'Hide connections' : `Expand ${displayName}`}
            </button>
            {error && <div className="connection-error">{error}</div>}
            {expanded && (
                connections.length === 0 ? (
                    <div className="connection-empty">No connected entities.</div>
                ) : (
                    <ul className="connection-list">
                        {connections.map((connection, index) => {
                            const neighborLabel = connection.node.labels[0] ?? 'Node'
                            const neighborKey = `${neighborLabel}:${connection.node.id}`
                            const properties = connection.node.properties
                            const neighborName = String(
                                properties.name
                                ?? properties.address
                                ?? properties[connection.node.idProperty]
                                ?? connection.node.id,
                            )
                            const isAncestor = ancestorKeys.includes(neighborKey) || neighborKey === nodeKey

                            return (
                                <li key={`${connection.relationshipType}:${neighborKey}:${index}`}>
                                    <div className="connection-edge">
                                        {connection.direction} {connection.relationshipType}
                                        {Object.keys(connection.relationshipProperties).length > 0 && (
                                            <span> {JSON.stringify(connection.relationshipProperties)}</span>
                                        )}
                                    </div>
                                    <div className="connection-node">
                                        <strong>{neighborName}</strong>
                                        <span>{connection.node.labels.join(':')} · {connection.node.id}</span>
                                    </div>
                                    <details className="connection-properties">
                                        <summary>Properties</summary>
                                        <pre>{JSON.stringify(properties, null, 2)}</pre>
                                    </details>
                                    {isAncestor ? (
                                        <div className="connection-cycle">Already shown in this path.</div>
                                    ) : (
                                        <RelationshipExplorer
                                            nodeLabel={neighborLabel}
                                            idProperty={connection.node.idProperty}
                                            nodeId={connection.node.id}
                                            displayName={neighborName}
                                            ancestorKeys={[...ancestorKeys, nodeKey]}
                                        />
                                    )}
                                </li>
                            )
                        })}
                    </ul>
                )
            )}
        </div>
    )
}

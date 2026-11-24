import { useEffect, useMemo, useState } from 'react'
import './OntologyMapping.css'

type PropertyMapping = {
    sourceField: string
    graphProperty: string
    description: string
}

type EntityMapping = {
    name: string
    labels: string[]
    description: string
    source: string
    fiboTarget: string | null
    properties: PropertyMapping[]
}

type RelationshipMapping = {
    name: string
    from: string[]
    to: string[]
    description: string
    source: string
    fiboTarget: string | null
    properties: PropertyMapping[]
}

type MappingModel = {
    fiboTargetsRecorded: boolean
    note: string
    entities: EntityMapping[]
    relationships: RelationshipMapping[]
}

type MappingItem = (EntityMapping & { kind: 'Entity' }) | (RelationshipMapping & { kind: 'Relationship' })

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export default function OntologyMapping() {
    const [model, setModel] = useState<MappingModel | null>(null)
    const [kind, setKind] = useState<'Entity' | 'Relationship'>('Entity')
    const [selectedName, setSelectedName] = useState('')
    const [filter, setFilter] = useState('')
    const [error, setError] = useState('')

    useEffect(() => {
        fetch(`${API_BASE}/loan/ontology-mappings`)
            .then(async (response) => {
                if (!response.ok) throw new Error(await response.text())
                setModel(await response.json() as MappingModel)
            })
            .catch((cause: unknown) => {
                setError(cause instanceof Error ? cause.message : String(cause))
            })
    }, [])

    const items = useMemo<MappingItem[]>(() => {
        if (!model) return []
        const allItems: MappingItem[] = [
            ...model.entities.map((item) => ({ ...item, kind: 'Entity' as const })),
            ...model.relationships.map((item) => ({ ...item, kind: 'Relationship' as const })),
        ]
        return allItems
            .filter((item) => item.kind === kind)
            .filter((item) => item.name.toLowerCase().includes(filter.toLowerCase()))
    }, [filter, kind, model])

    const selected = items.find((item) => item.name === selectedName) ?? items[0]

    return (
        <div className="ontology-mapping-page">
            <div className="mapping-heading">
                <div>
                    <h1>Ontology Mapping</h1>
                    <p>Loan graph model and its source-field mappings</p>
                </div>
                <div className="mapping-kind-toggle" role="group" aria-label="Mapping kind">
                    <button className={kind === 'Entity' ? 'selected' : ''} onClick={() => { setKind('Entity'); setSelectedName('') }}>
                        Entities
                    </button>
                    <button className={kind === 'Relationship' ? 'selected' : ''} onClick={() => { setKind('Relationship'); setSelectedName('') }}>
                        Relationships
                    </button>
                </div>
            </div>

            {model && !model.fiboTargetsRecorded && (
                <div className="mapping-note">{model.note}</div>
            )}
            {error && <pre className="mapping-error">{error}</pre>}

            <div className="mapping-workspace">
                <aside className="mapping-index">
                    <input
                        value={filter}
                        onChange={(event) => setFilter(event.target.value)}
                        placeholder={`Filter ${kind.toLowerCase()}s`}
                        aria-label={`Filter ${kind.toLowerCase()}s`}
                    />
                    {items.map((item) => (
                        <button
                            key={`${item.kind}:${item.name}`}
                            className={selected?.name === item.name ? 'mapping-index-item selected' : 'mapping-index-item'}
                            onClick={() => setSelectedName(item.name)}
                        >
                            <strong>{item.name}</strong>
                            <span>{item.kind === 'Entity' ? item.source : `${item.from.join(', ')} → ${item.name} → ${item.to.join(', ')}`}</span>
                        </button>
                    ))}
                </aside>

                <section className="mapping-detail">
                    {!selected ? (
                        <p>No {kind.toLowerCase()} mappings match this filter.</p>
                    ) : (
                        <>
                            <div className="mapping-detail-heading">
                                <span className="mapping-kind-label">{selected.kind}</span>
                                <h2>{selected.name}</h2>
                                <p>{selected.description}</p>
                            </div>
                            <dl className="mapping-metadata">
                                <div><dt>Source</dt><dd>{selected.source}</dd></div>
                                <div><dt>FIBO target</dt><dd>{selected.fiboTarget ?? 'Not recorded in the model'}</dd></div>
                                {selected.kind === 'Entity' && <div><dt>Graph labels</dt><dd>{selected.labels.join(', ')}</dd></div>}
                                {selected.kind === 'Relationship' && <div><dt>Direction</dt><dd>{selected.from.join(', ')} → {selected.to.join(', ')}</dd></div>}
                            </dl>
                            <h3>Field mappings</h3>
                            <div className="mapping-property-list">
                                {selected.properties.map((property) => (
                                    <article className="mapping-property" key={`${property.sourceField}:${property.graphProperty}`}>
                                        <div className="mapping-property-path">
                                            <code>{property.sourceField}</code>
                                            <span>→</span>
                                            <code>{property.graphProperty}</code>
                                        </div>
                                        <p>{property.description || 'No description recorded.'}</p>
                                    </article>
                                ))}
                                {selected.properties.length === 0 && <p>No property mappings recorded.</p>}
                            </div>
                        </>
                    )}
                </section>
            </div>
        </div>
    )
}

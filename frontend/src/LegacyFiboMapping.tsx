import { useEffect, useMemo, useState } from 'react'
import './LegacyFiboMapping.css'

type SourceCatalog = {
    sourceSystem: string
    sourceFile: string
    elements: LegacySource[]
}

type TargetCatalog = {
    classes: { name: string; description: string }[]
    properties: { name: string; domain: string; description: string }[]
    relationships: { name: string; description: string }[]
}

type LegacySource = {
    sourceRef: string
    sourceKind: 'entity' | 'field' | 'relationship'
    sourceTable: string
    sourceField: string | null
    graphElement: string
    description: string
    fiboTargetKind: 'class' | 'property' | 'relationship'
    semanticExample?: string | null
}

type FiboMapping = {
    id: number
    source_ref: string
    source_kind: LegacySource['sourceKind']
    source_table: string
    source_field: string | null
    graph_element: string
    fibo_target_kind: 'class' | 'property' | 'relationship'
    fibo_iri: string | null
    fibo_label: string
    rationale: string
    is_cde: boolean
    cde_definition: string | null
    review_status: 'draft' | 'reviewed'
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

const mappingSuggestions: Record<string, { label: string; domain?: string; rationale: string }> = {
    'entity|SQL_Q1': {
        label: 'Loan',
        rationale: 'Candidate: Query 1 returns one loan-level result row. Review that this result represents a Loan entity before saving.',
    },
    'field|SQL_Q1|LOAN_ID': {
        label: 'loanId', domain: 'Loan',
        rationale: 'Candidate: the output LOAN_ID identifies the loan represented by each query row.',
    },
    'field|SQL_Q1|ORIGINAL_AMOUNT': {
        label: 'principalAmount', domain: 'Loan',
        rationale: 'Candidate: the output is sourced from ORIG_AMT. Confirm it has the same meaning as loan principal.',
    },
    'field|SQL_Q1|OUTSTANDING_BALANCE': {
        label: 'currentBalance', domain: 'Loan',
        rationale: 'Candidate: the output is sourced from OUT_BAL and represents outstanding loan balance.',
    },
    'field|SQL_Q1|MATURITY_DT': {
        label: 'maturityDate', domain: 'Loan',
        rationale: 'Candidate: the output is sourced from the loan maturity date.',
    },
    'field|SQL_Q4|OUTSTANDING_BALANCE': {
        label: 'currentBalance', domain: 'Loan',
        rationale: 'Candidate: this output carries the loan outstanding balance used in the collateral coverage calculation.',
    },
    'clause|SQL_Q1|join|1': {
        label: 'BORROWER_ON',
        rationale: 'Candidate: this join connects the loan borrower identifier to the customer identifier. Confirm identity resolution and relationship direction before saving.',
    },
    'clause|SQL_Q2|join|1': {
        label: 'BORROWER_ON',
        rationale: 'Candidate: this join associates customer rows with their loans. Confirm the customer represents a Person in the target graph.',
    },
}

export default function LegacyFiboMapping() {
    const [sources, setSources] = useState<LegacySource[]>([])
    const [mappings, setMappings] = useState<FiboMapping[]>([])
    const [targets, setTargets] = useState<TargetCatalog>({ classes: [], properties: [], relationships: [] })
    const [selectedRef, setSelectedRef] = useState('')
    const [filter, setFilter] = useState('')
    const [fiboLabel, setFiboLabel] = useState('')
    const [rationale, setRationale] = useState('')
    const [isCde, setIsCde] = useState(false)
    const [cdeDefinition, setCdeDefinition] = useState('')
    const [error, setError] = useState('')
    const [saving, setSaving] = useState(false)

    async function loadMappings() {
        const response = await fetch(`${API_BASE}/legacy-fibo-mapping/mappings`)
        if (!response.ok) throw new Error(await response.text())
        setMappings(await response.json() as FiboMapping[])
    }

    async function syncLineageGraph() {
        const response = await fetch(`${API_BASE}/sql-lineage/sync`, { method: 'POST' })
        if (!response.ok) {
            throw new Error(`Mapping saved in PostgreSQL, but Neo4j lineage sync failed: ${await response.text()}`)
        }
    }

    useEffect(() => {
        Promise.all([
            fetch(`${API_BASE}/legacy-fibo-mapping/sources`).then(async (response) => {
                if (!response.ok) throw new Error(await response.text())
                return await response.json() as SourceCatalog
            }),
            fetch(`${API_BASE}/legacy-fibo-mapping/mappings`).then(async (response) => {
                if (!response.ok) throw new Error(await response.text())
                return await response.json() as FiboMapping[]
            }),
            fetch(`${API_BASE}/legacy-fibo-mapping/targets`).then(async (response) => {
                if (!response.ok) throw new Error(await response.text())
                return await response.json() as TargetCatalog
            }),
        ]).then(([catalog, existingMappings, graphTargets]) => {
            setSources(catalog.elements)
            setMappings(existingMappings)
            setTargets(graphTargets)
        }).catch((cause: unknown) => {
            setError(cause instanceof Error ? cause.message : String(cause))
        })
    }, [])

    useEffect(() => {
        if (!selectedRef && sources.length > 0) setSelectedRef(sources[0].sourceRef)
    }, [selectedRef, sources])

    const selectedSource = sources.find((source) => source.sourceRef === selectedRef)
    const selectedMapping = mappings.find((mapping) => mapping.source_ref === selectedRef)
    const suggestion = selectedSource ? mappingSuggestions[selectedSource.sourceRef] : undefined
    const targetOptions = selectedSource?.fiboTargetKind === 'class'
        ? targets.classes.map((item) => ({ name: item.name, domain: '', description: item.description }))
        : selectedSource?.fiboTargetKind === 'relationship'
            ? targets.relationships.map((item) => ({ name: item.name, domain: '', description: item.description }))
            : targets.properties.map((item) => ({ name: item.name, domain: item.domain, description: item.description }))
    const selectedTargetExists = targetOptions.some((item) => item.name === fiboLabel)
    const suggestedTargetName = suggestion
        ? (suggestion.domain ? `${suggestion.domain}.${suggestion.label}` : suggestion.label)
        : ''
    const filteredSources = useMemo(() => {
        const needle = filter.trim().toLowerCase()
        if (!needle) return sources
        return sources.filter((source) =>
            `${source.sourceTable} ${source.sourceField ?? ''} ${source.graphElement} ${source.description}`
                .toLowerCase()
                .includes(needle),
        )
    }, [filter, sources])

    useEffect(() => {
        setFiboLabel(selectedMapping?.fibo_label ?? '')
        setRationale(selectedMapping?.rationale ?? '')
        setIsCde(selectedMapping?.is_cde ?? false)
        setCdeDefinition(selectedMapping?.cde_definition ?? '')
    }, [selectedRef, selectedMapping?.id])

    async function saveMapping(reviewStatus: 'draft' | 'reviewed' = 'draft') {
        if (!selectedSource) return
        setSaving(true)
        setError('')

        const payload = {
            source_ref: selectedSource.sourceRef,
            source_kind: selectedSource.sourceKind,
            source_table: selectedSource.sourceTable,
            source_field: selectedSource.sourceField,
            graph_element: selectedSource.graphElement,
            fibo_target_kind: selectedSource.fiboTargetKind,
            fibo_iri: selectedMapping?.fibo_iri ?? null,
            fibo_label: fiboLabel.trim(),
            rationale: rationale.trim(),
            is_cde: selectedSource.sourceKind === 'field' && isCde,
            cde_definition: selectedSource.sourceKind === 'field' && isCde ? cdeDefinition.trim() : null,
            review_status: reviewStatus,
        }

        try {
            const response = await fetch(
                selectedMapping
                    ? `${API_BASE}/legacy-fibo-mapping/mappings/${selectedMapping.id}`
                    : `${API_BASE}/legacy-fibo-mapping/mappings`,
                {
                    method: selectedMapping ? 'PUT' : 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                },
            )
            if (!response.ok) throw new Error(await response.text())
            await loadMappings()
            await syncLineageGraph()
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause))
        } finally {
            setSaving(false)
        }
    }

    async function deleteMapping() {
        if (!selectedMapping) return
        setError('')
        try {
            const response = await fetch(
                `${API_BASE}/legacy-fibo-mapping/mappings/${selectedMapping.id}`,
                { method: 'DELETE' },
            )
            if (!response.ok) throw new Error(await response.text())
            await loadMappings()
            await syncLineageGraph()
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause))
        }
    }

    return (
        <div className="legacy-fibo-page">
            <div className="legacy-fibo-heading">
                <div>
                    <h1>Legacy → FIBO Mapping</h1>
                <p>Map legacy entities, fields, and relationships to the current loan graph vocabulary.</p>
                </div>
                <span>{mappings.length} saved mappings</span>
            </div>

            <div className="legacy-fibo-note">
                Sources are query outputs and join predicates from fibo/sql/sql.sql. The current loan graph supplies exact target terms. IRIs are omitted for now; suggestions are candidates, not confirmed mappings.
            </div>
            {error && <pre className="legacy-fibo-error">{error}</pre>}

            <div className="legacy-fibo-workspace">
                <aside className="legacy-fibo-sources">
                    <input
                        value={filter}
                        onChange={(event) => setFilter(event.target.value)}
                        placeholder="Filter legacy entities and fields"
                        aria-label="Filter legacy sources"
                    />
                    {filteredSources.map((source) => {
                        const mapping = mappings.find((item) => item.source_ref === source.sourceRef)
                        return (
                            <button
                                key={source.sourceRef}
                                className={selectedRef === source.sourceRef ? 'legacy-source selected' : 'legacy-source'}
                                onClick={() => setSelectedRef(source.sourceRef)}
                            >
                                <strong>{source.sourceKind === 'relationship' ? source.graphElement : source.sourceField ? `${source.sourceTable}.${source.sourceField}` : source.sourceTable}</strong>
                                <span>{source.sourceKind} → FIBO {source.fiboTargetKind}</span>
                                {mapping && <span className={`mapping-status ${mapping.review_status}`}>{mapping.review_status}{mapping.is_cde ? ' · CDE' : ''}</span>}
                            </button>
                        )
                    })}
                </aside>

                <section className="legacy-fibo-editor">
                    {!selectedSource ? (
                        <p>Loading source fields…</p>
                    ) : (
                        <>
                            <div className="legacy-source-summary">
                                <span>{selectedSource.sourceKind} → FIBO {selectedSource.fiboTargetKind}</span>
                                <h2>{selectedSource.sourceKind === 'relationship' ? selectedSource.graphElement : selectedSource.sourceField ? `${selectedSource.sourceTable}.${selectedSource.sourceField}` : selectedSource.sourceTable}</h2>
                                <p>{selectedSource.description}</p>
                                <small>Legacy source element: {selectedSource.graphElement}</small>
                                {selectedSource.semanticExample && <div className="legacy-semantic-example"><strong>Data dictionary example</strong><span>{selectedSource.semanticExample}</span></div>}
                            </div>

                            <div className="fibo-target-fields">
                                <label>
                                    Current graph {selectedSource.fiboTargetKind}
                                    <select value={fiboLabel} onChange={(event) => setFiboLabel(event.target.value)}>
                                        <option value="">Choose an exact graph {selectedSource.fiboTargetKind}</option>
                                        {fiboLabel && !selectedTargetExists && <option value={fiboLabel}>Unavailable in current graph: {fiboLabel}</option>}
                                        {targetOptions.map((item) => <option key={item.name} value={item.name} title={item.description}>{item.name}</option>)}
                                    </select>
                                </label>
                                <label>
                                    Mapping rationale
                                    <textarea value={rationale} onChange={(event) => setRationale(event.target.value)} rows={3} placeholder="Why this legacy element maps to this FIBO term" />
                                </label>
                            </div>

                            {suggestion && (
                                <div className="legacy-semantic-example">
                                    <strong>Suggested graph target · verify before saving</strong>
                                    <span>{suggestedTargetName} — {suggestion.rationale}</span>
                                    <button type="button" onClick={() => { setFiboLabel(suggestedTargetName); setRationale(suggestion.rationale) }}>Use suggestion</button>
                                </div>
                            )}

                            {selectedSource.sourceKind === 'field' && (
                                <fieldset className="cde-fields">
                                    <legend>Critical Data Element</legend>
                                    <label className="cde-toggle">
                                        <input type="checkbox" checked={isCde} onChange={(event) => setIsCde(event.target.checked)} />
                                        Mark this legacy field as a CDE
                                    </label>
                                    {isCde && (
                                        <label>
                                            CDE definition
                                            <textarea value={cdeDefinition} onChange={(event) => setCdeDefinition(event.target.value)} rows={3} placeholder="Define the business meaning and why this field is critical" />
                                        </label>
                                    )}
                                </fieldset>
                            )}

                            <div className="mapping-editor-actions">
                                <span>{selectedMapping ? `Status: ${selectedMapping.review_status}` : 'Not mapped yet'}</span>
                                <div>
                                    {selectedMapping && <button className="mapping-delete" onClick={() => void deleteMapping()}>Delete</button>}
                                    {selectedMapping?.review_status !== 'reviewed' && (
                                        <button onClick={() => void saveMapping('reviewed')} disabled={saving || !selectedTargetExists || (isCde && !cdeDefinition.trim())}>Mark reviewed</button>
                                    )}
                                    <button className="mapping-save" onClick={() => void saveMapping('draft')} disabled={saving || !selectedTargetExists || (isCde && !cdeDefinition.trim())}>
                                        {saving ? 'Saving…' : selectedMapping ? 'Save changes' : 'Save mapping'}
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                </section>
            </div>
        </div>
    )
}

import { useEffect, useMemo, useState } from 'react'
import './SqlLineage.css'

type GraphTerm = {
    termKey: string
    termKind: 'class' | 'property' | 'relationship'
    name: string
    domain?: string
}

type TargetLink = {
    term: GraphTerm
    status: 'draft' | 'reviewed'
    relationshipType: 'MAPS_TO' | 'PROPOSES_MAPPING_TO'
}

type InputColumn = {
    sourceRef: string
    name: string
    tableName: string
    columnName: string
}

type OutputColumn = {
    sourceRef: string
    name: string
    position: number
    sqlExpression: string
    expressionKind: 'direct' | 'derived' | 'aggregate'
    isCde: boolean
    cdeDefinition: string | null
    mappingRationale: string | null
    sourceColumns: InputColumn[]
    mappings: TargetLink[]
}

type SqlClause = {
    clauseKind: 'join' | 'filter' | 'grouping'
    sqlExpression: string
    sourceColumns: InputColumn[]
    mappings: TargetLink[]
    mappingRationale: string | null
}

type SqlQuery = {
    queryId: string
    queryNumber: number
    name: string
    lineStart: number
    sqlStatement: string
    tables: string[]
    clauses: SqlClause[]
    mappings: TargetLink[]
    outputs: OutputColumn[]
}

type LineageResponse = {
    synced: boolean
    sourceFile: string
    sourceHash?: string
    syncedAt?: string
    summary?: { queries: number; outputColumns: number; mappedOutputs: number; cdes: number }
    queries: SqlQuery[]
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export default function SqlLineage() {
    const [lineage, setLineage] = useState<LineageResponse | null>(null)
    const [selectedQueryId, setSelectedQueryId] = useState('')
    const [selectedOutputRef, setSelectedOutputRef] = useState('')
    const [error, setError] = useState('')
    const [syncing, setSyncing] = useState(false)

    async function loadLineage() {
        const response = await fetch(`${API_BASE}/sql-lineage`)
        if (!response.ok) throw new Error(await response.text())
        const result = await response.json() as LineageResponse
        setLineage(result)
        if (!selectedQueryId && result.queries[0]) setSelectedQueryId(result.queries[0].queryId)
    }

    useEffect(() => {
        void loadLineage().catch((cause: unknown) => setError(cause instanceof Error ? cause.message : String(cause)))
    }, [])

    const selectedQuery = useMemo(
        () => lineage?.queries.find((query) => query.queryId === selectedQueryId),
        [lineage, selectedQueryId],
    )
    const selectedOutput = selectedQuery?.outputs.find((output) => output.sourceRef === selectedOutputRef)

    useEffect(() => {
        if (selectedQuery && !selectedQuery.outputs.some((output) => output.sourceRef === selectedOutputRef)) {
            setSelectedOutputRef(selectedQuery.outputs[0]?.sourceRef ?? '')
        }
    }, [selectedQuery, selectedOutputRef])

    async function syncLineage() {
        setSyncing(true)
        setError('')
        try {
            const response = await fetch(`${API_BASE}/sql-lineage/sync`, { method: 'POST' })
            if (!response.ok) throw new Error(await response.text())
            await loadLineage()
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause))
        } finally {
            setSyncing(false)
        }
    }

    function targetLabel(mapping: TargetLink) {
        return mapping.term.name
    }

    return (
        <div className="sql-lineage-page">
            <header className="sql-lineage-heading">
                <div>
                    <h1>SQL Lineage</h1>
                    <p>Follow SQL result columns from legacy inputs into the current loan graph vocabulary.</p>
                </div>
                <button className="lineage-sync-button" onClick={() => void syncLineage()} disabled={syncing}>
                    {syncing ? 'Syncing…' : lineage?.synced ? 'Sync SQL to Neo4j' : 'Build lineage in Neo4j'}
                </button>
            </header>

            <div className="sql-lineage-scope">
                Source: <strong>{lineage?.sourceFile ?? 'fibo/sql/sql.sql'}</strong>. Output expressions, input columns, joins, filters, graph terms, and mapping/CDE status are connected in Neo4j. Mapping decisions remain in PostgreSQL.
            </div>
            {error && <pre className="sql-lineage-error">{error}</pre>}

            {!lineage?.synced ? (
                <div className="lineage-empty-state">
                    <h2>Lineage has not been built in Neo4j</h2>
                    <p>Build it from the six SELECT statements in sql.sql. This creates query, output-column, source-column, and graph-term links in the existing Aura database.</p>
                    <button onClick={() => void syncLineage()} disabled={syncing}>{syncing ? 'Building…' : 'Build graph lineage'}</button>
                </div>
            ) : (
                <>
                    <div className="sql-lineage-stats">
                        <div><strong>{lineage.summary?.queries ?? 0}</strong><span>SQL queries</span></div>
                        <div><strong>{lineage.summary?.outputColumns ?? 0}</strong><span>Output columns</span></div>
                        <div><strong>{lineage.summary?.mappedOutputs ?? 0}</strong><span>Linked to graph terms</span></div>
                        <div><strong>{lineage.summary?.cdes ?? 0}</strong><span>CDEs</span></div>
                    </div>
                    <div className="lineage-sync-metadata">Persisted in Neo4j · source SHA-256 {lineage.sourceHash?.slice(0, 16)}… · synced {lineage.syncedAt}</div>

                    <div className="sql-lineage-workspace">
                        <aside className="sql-lineage-table-list">
                            <h2>SQL statements</h2>
                            {lineage.queries.map((query) => (
                                <button
                                    key={query.queryId}
                                    className={selectedQueryId === query.queryId ? 'lineage-table-option selected' : 'lineage-table-option'}
                                    onClick={() => setSelectedQueryId(query.queryId)}
                                >
                                    <strong>{query.name}</strong>
                                    <span>{query.outputs.length} outputs · lines {query.lineStart}+</span>
                                    {query.mappings.map((mapping) => <span key={mapping.term.termKey} className="lineage-sidebar-target">→ {targetLabel(mapping)}</span>)}
                                </button>
                            ))}
                        </aside>

                        {selectedQuery && (
                            <>
                                <section className="sql-lineage-columns">
                                    <div className="lineage-section-heading">
                                        <div>
                                            <span>Query {selectedQuery.queryNumber} · line {selectedQuery.lineStart}</span>
                                            <h2>{selectedQuery.name}</h2>
                                            <p>Reads from: {selectedQuery.tables.join(', ')}</p>
                                        </div>
                                        {selectedQuery.mappings.map((mapping) => <span key={mapping.term.termKey} className="lineage-mapping-chip">{mapping.term.name}</span>)}
                                    </div>

                                    <div className="lineage-column-list">
                                        {selectedQuery.outputs.map((output) => (
                                            <button
                                                key={output.sourceRef}
                                                className={selectedOutputRef === output.sourceRef ? 'lineage-column selected' : 'lineage-column'}
                                                onClick={() => setSelectedOutputRef(output.sourceRef)}
                                            >
                                                <span className="lineage-column-name"><strong>{output.name}</strong><small>{output.expressionKind}</small></span>
                                                <span className="lineage-column-tags">
                                                    {output.mappings.map((mapping) => <b key={mapping.term.termKey}>{mapping.term.name}</b>)}
                                                    {output.isCde && <em>CDE</em>}
                                                </span>
                                            </button>
                                        ))}
                                    </div>

                                    {selectedOutput && (
                                        <div className="lineage-expression">
                                            <h3>SQL expression</h3>
                                            <code>{selectedOutput.sqlExpression}</code>
                                            <span>Derived from {selectedOutput.sourceColumns.map((column) => `${column.tableName}.${column.columnName}`).join(', ') || 'no source column identified'}</span>
                                        </div>
                                    )}
                                    <div className="lineage-expression">
                                        <h3>Query clauses</h3>
                                        {selectedQuery.clauses.map((clause, index) => (
                                            <div className="lineage-clause" key={`${clause.clauseKind}:${index}`}>
                                                <strong>{clause.clauseKind}</strong>
                                                <code>{clause.sqlExpression}</code>
                                                <span>Columns: {clause.sourceColumns.map((column) => `${column.tableName}.${column.columnName}`).join(', ') || 'none identified'}</span>
                                                {clause.mappings.map((mapping) => <span key={mapping.term.termKey}>Graph relationship: {mapping.term.name} · {mapping.relationshipType === 'MAPS_TO' ? 'reviewed link' : 'draft proposal'}</span>)}
                                                {clause.mappingRationale && <span>{clause.mappingRationale}</span>}
                                            </div>
                                        ))}
                                        {selectedQuery.clauses.length === 0 && <span>No JOIN, WHERE, or GROUP BY clauses detected.</span>}
                                    </div>
                                </section>

                                <aside className="sql-lineage-detail">
                                    {!selectedOutput ? <p>Select an output column.</p> : (
                                        <>
                                            <span>{selectedOutput.expressionKind} output · position {selectedOutput.position}</span>
                                            <h2>{selectedQuery.queryId}.{selectedOutput.name}</h2>
                                            <div className="lineage-detail-block">
                                                <strong>Input lineage</strong>
                                                {selectedOutput.sourceColumns.length
                                                    ? selectedOutput.sourceColumns.map((column) => <p key={column.sourceRef}>{column.tableName}.{column.columnName}</p>)
                                                    : <p>No column references identified in this expression.</p>}
                                            </div>
                                            <div className="lineage-detail-block">
                                                <strong>Current graph link</strong>
                                                {selectedOutput.mappings.length
                                                    ? selectedOutput.mappings.map((mapping) => (
                                                        <p key={mapping.term.termKey}>
                                                            <b>{mapping.term.name}</b> · {mapping.relationshipType === 'MAPS_TO' ? 'reviewed link' : 'draft proposal'}
                                                        </p>
                                                    ))
                                                    : <p>No saved mapping connects this output to a graph term yet.</p>}
                                                {selectedOutput.mappingRationale && <p>{selectedOutput.mappingRationale}</p>}
                                            </div>
                                            {selectedOutput.isCde && (
                                                <div className="lineage-cde">
                                                    <strong>Critical Data Element</strong>
                                                    <p>{selectedOutput.cdeDefinition || 'CDE; no definition supplied.'}</p>
                                                </div>
                                            )}
                                            <details className="lineage-sql-source">
                                                <summary>View full SQL statement</summary>
                                                <pre>{selectedQuery.sqlStatement}</pre>
                                            </details>
                                        </>
                                    )}
                                </aside>
                            </>
                        )}
                    </div>
                </>
            )}
        </div>
    )
}

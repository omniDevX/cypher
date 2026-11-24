import { useEffect, useState } from 'react'
import './SqlLineageOwl.css'

type SavedSqlQuery = {
    id: number
    name: string
    sql: string
    created_at: string
}

type GraphTerm = {
    termKey: string
    termKind: 'class' | 'property' | 'relationship'
    name: string
}

type TargetLink = {
    term: GraphTerm
    status: 'draft' | 'reviewed'
    relationshipType: 'MAPS_TO' | 'PROPOSES_MAPPING_TO'
}

type InputColumn = {
    sourceRef: string
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
    summary?: { queries: number; outputColumns: number; mappedOutputs: number; cdes: number }
    queries: SqlQuery[]
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export default function SqlLineageOwl() {
    const [savedQueries, setSavedQueries] = useState<SavedSqlQuery[]>([])
    const [sql, setSql] = useState('')
    const [selectedQueryId, setSelectedQueryId] = useState<number | null>(null)
    const [lineage, setLineage] = useState<LineageResponse | null>(null)
    const [selectedOutputRef, setSelectedOutputRef] = useState('')
    const [error, setError] = useState('')
    const [analyzing, setAnalyzing] = useState(false)

    async function loadSavedQueries() {
        const response = await fetch(`${API_BASE}/sql-lineage/saved-queries`)
        if (!response.ok) throw new Error(await response.text())
        setSavedQueries(await response.json() as SavedSqlQuery[])
    }

    useEffect(() => {
        void loadSavedQueries().catch((cause: unknown) => {
            setError(cause instanceof Error ? cause.message : String(cause))
        })
    }, [])

    const selectedQuery = lineage?.queries[0]
    const selectedOutput = selectedQuery?.outputs.find((output) => output.sourceRef === selectedOutputRef)

    async function runLineage() {
        if (!sql.trim()) return
        setError('')
        setLineage(null)
        setSelectedOutputRef('')
        setAnalyzing(true)
        try {
            const response = await fetch(`${API_BASE}/sql-lineage/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sql }),
            })
            if (!response.ok) throw new Error(await response.text())
            const result = await response.json() as LineageResponse
            setLineage(result)
            setSelectedOutputRef(result.queries[0]?.outputs[0]?.sourceRef ?? '')
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause))
        } finally {
            setAnalyzing(false)
        }
    }

    function selectSavedQuery(query: SavedSqlQuery) {
        setSelectedQueryId(query.id)
        setLineage(null)
        setSelectedOutputRef('')
        setError('')
        setSql(query.sql)
    }

    return (
        <div className="sql-lineage-owl">
            <header className="sql-lineage-owl-heading">
                <div>
                    <h1>SQL Lineage OWL</h1>
                    <p>Enter SQL or choose a saved statement, then run lineage.</p>
                </div>
                <textarea
                    className="sql-lineage-owl-input"
                    aria-label="SQL to analyze"
                    value={sql}
                    onChange={(event) => {
                        setSql(event.target.value)
                        setSelectedQueryId(null)
                        setLineage(null)
                        setSelectedOutputRef('')
                    }}
                    placeholder="Type or paste a SQL statement…"
                    rows={4}
                />
                <button
                    className="sql-lineage-owl-run"
                    onClick={() => void runLineage()}
                    disabled={analyzing || !sql.trim()}
                >
                    {analyzing ? 'Building lineage…' : 'Lineage'}
                </button>
            </header>
            {error && <pre className="sql-lineage-error">{error}</pre>}

            <div className="sql-lineage-owl-workspace">
                <main className="sql-lineage-owl-results">
                    {!selectedQuery ? (
                        <div className="sql-lineage-owl-empty">
                            <h2>{analyzing ? 'Building lineage…' : 'Select a saved SQL query'}</h2>
                            <p>Choose a query from the right pane to trace its output columns, source fields, clauses, and graph links.</p>
                        </div>
                    ) : (
                        <>
                            <div className="sql-lineage-owl-query-heading">
                                <span>{selectedQuery.tables.length ? `Reads from ${selectedQuery.tables.join(', ')}` : lineage?.sourceFile}</span>
                                <h2>{selectedQuery.name}</h2>
                                <p>{selectedQuery.outputs.length} output columns · {selectedQuery.clauses.length} clauses</p>
                            </div>

                            <section className="sql-lineage-owl-section">
                                <h3>Output columns</h3>
                                <div className="sql-lineage-owl-output-list">
                                    {selectedQuery.outputs.map((output) => (
                                        <button
                                            key={output.sourceRef}
                                            className={selectedOutputRef === output.sourceRef ? 'sql-lineage-owl-output selected' : 'sql-lineage-owl-output'}
                                            onClick={() => setSelectedOutputRef(output.sourceRef)}
                                        >
                                            <span><strong>{output.name}</strong><small>{output.expressionKind}</small></span>
                                            <span className="sql-lineage-owl-tags">
                                                {output.mappings.map((mapping) => <b key={mapping.term.termKey}>{mapping.term.name}</b>)}
                                                {output.isCde && <em>CDE</em>}
                                            </span>
                                        </button>
                                    ))}
                                    {!selectedQuery.outputs.length && <p>No output columns were identified by the lineage parser.</p>}
                                </div>
                            </section>

                            {selectedOutput && (
                                <section className="sql-lineage-owl-section">
                                    <h3>Selected output lineage · {selectedOutput.name}</h3>
                                    <code className="sql-lineage-owl-expression">{selectedOutput.sqlExpression}</code>
                                    <p>
                                        Derived from {selectedOutput.sourceColumns.map((column) => `${column.tableName}.${column.columnName}`).join(', ') || 'no source column identified'}
                                    </p>
                                    {selectedOutput.mappings.map((mapping) => (
                                        <p key={mapping.term.termKey} className="sql-lineage-owl-mapping">
                                            {mapping.term.name} · {mapping.relationshipType === 'MAPS_TO' ? 'reviewed link' : 'draft proposal'}
                                        </p>
                                    ))}
                                    {selectedOutput.mappingRationale && <p>{selectedOutput.mappingRationale}</p>}
                                    {selectedOutput.isCde && (
                                        <div className="sql-lineage-owl-cde">
                                            <strong>Critical Data Element</strong>
                                            <p>{selectedOutput.cdeDefinition || 'CDE; no definition supplied.'}</p>
                                        </div>
                                    )}
                                </section>
                            )}

                            <section className="sql-lineage-owl-section">
                                <h3>Query clauses</h3>
                                {selectedQuery.clauses.map((clause, index) => (
                                    <div className="sql-lineage-owl-clause" key={`${clause.clauseKind}:${index}`}>
                                        <strong>{clause.clauseKind}</strong>
                                        <code>{clause.sqlExpression}</code>
                                        <span>Columns: {clause.sourceColumns.map((column) => `${column.tableName}.${column.columnName}`).join(', ') || 'none identified'}</span>
                                        {clause.mappings.map((mapping) => (
                                            <span key={mapping.term.termKey}>
                                                Graph relationship: {mapping.term.name} · {mapping.relationshipType === 'MAPS_TO' ? 'reviewed link' : 'draft proposal'}
                                            </span>
                                        ))}
                                        {clause.mappingRationale && <span>{clause.mappingRationale}</span>}
                                    </div>
                                ))}
                                {!selectedQuery.clauses.length && <p>No JOIN, WHERE, or GROUP BY clauses detected.</p>}
                            </section>

                            <details className="sql-lineage-owl-sql">
                                <summary>View full SQL statement</summary>
                                <pre>{selectedQuery.sqlStatement}</pre>
                            </details>
                        </>
                    )}
                </main>

                <aside className="sql-lineage-owl-saved">
                    <h2>Saved SQL</h2>
                    <div className="sql-lineage-owl-list">
                        {savedQueries.map((query) => (
                            <button
                                key={query.id}
                                className={selectedQueryId === query.id ? 'sql-lineage-owl-saved-query selected' : 'sql-lineage-owl-saved-query'}
                                onClick={() => selectSavedQuery(query)}
                                title={query.sql}
                            >
                                <strong>{query.name}</strong>
                                <span>{query.sql.trim().replace(/\s+/g, ' ').slice(0, 100)}</span>
                            </button>
                        ))}
                        {!savedQueries.length && <p>No SQL saved yet.</p>}
                    </div>
                </aside>
            </div>
        </div>
    )
}

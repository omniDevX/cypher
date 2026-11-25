import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import BorrowerProfile, { type BorrowerProfileData } from './BorrowerProfile'
import OntologyMapping from './OntologyMapping'
import LegacyFiboMapping from './LegacyFiboMapping'
import SqlLineage from './SqlLineage'
import SqlLineageOwl from './SqlLineageOwl'
import { loadBorrowerProfile, loadSavedQueries, type SavedQuery } from './components/loading'
import './css/App.css'

type BorrowerOption = {
    borrowerId: string
    borrowerName: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

function App() {
    const queryEditor = useRef<HTMLTextAreaElement>(null)
    const [query, setQuery] = useState('')
    const [queryName, setQueryName] = useState('')
    const [result, setResult] = useState<unknown>(null)
    const [savedQueries, setSavedQueries] = useState<SavedQuery[]>([])
    const [savedQueriesLoading, setSavedQueriesLoading] = useState(true)
    const [borrowers, setBorrowers] = useState<BorrowerOption[]>([])
    const [borrowersLoading, setBorrowersLoading] = useState(true)
    const [selectedBorrowerId, setSelectedBorrowerId] = useState('')
    const [borrowerProfile, setBorrowerProfile] = useState<BorrowerProfileData | null>(null)
    const [borrowerProfileLoading, setBorrowerProfileLoading] = useState(false)
    const [error, setError] = useState('')
    const [running, setRunning] = useState(false)
    const [activePage, setActivePage] = useState<'explore' | 'mapping' | 'legacy-fibo' | 'sql-lineage' | 'sql-lineage-owl'>('explore')

    useEffect(() => {
        loadSavedQueries()
            .then(setSavedQueries)
            .catch((cause: unknown) => {
                setError(cause instanceof Error ? cause.message : String(cause))
            })
            .finally(() => setSavedQueriesLoading(false))

        fetch(`${API_BASE}/loan/borrowers`)
            .then(async (response) => {
                if (!response.ok) throw new Error(await response.text())
                setBorrowers(await response.json() as BorrowerOption[])
            })
            .catch((cause: unknown) => {
                setError(cause instanceof Error ? cause.message : String(cause))
            })
            .finally(() => setBorrowersLoading(false))
    }, [])


    async function runQuery(cypher = query) {
        if (!cypher.trim()) return
        setRunning(true)
        setError('')
        try {
            const response = await fetch(`${API_BASE}/neo4j/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cypher, parameters: {} }),
            })
            const responseText = await response.text()
            let body: unknown
            try {
                body = responseText ? JSON.parse(responseText) : null
            } catch {
                body = responseText
            }
            if (!response.ok) {
                throw new Error(typeof body === 'string' ? body : JSON.stringify(body))
            }
            setResult(body)
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause))
        } finally {
            setRunning(false)
        }
    }

    async function saveQuery() {
        if (!query.trim() || !queryName.trim()) return
        setError('')
        try {
            const response = await fetch(`${API_BASE}/neo4j/saved-queries`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: queryName.trim(), cypher: query }),
            })
            if (!response.ok) throw new Error(await response.text())
            setQueryName('')
            setSavedQueriesLoading(true)
            setSavedQueries(await loadSavedQueries())
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : String(cause))
        } finally {
            setSavedQueriesLoading(false)
        }
    }

    function handleQueryKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            void runQuery()
        }
    }

    return (
        <div className="app">
            <header className="topbar">
                <div className="brand-block">
                    <strong className="brand">Knowledge Graph</strong>
                    <span className="brand-version" title="Application version and deployment commit">
                        v112301
                    </span>
                </div>
                <textarea
                    ref={queryEditor}
                    className="search"
                    placeholder="Enter Cypher query..."
                    rows={4}
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    onKeyDown={handleQueryKeyDown}
                />
                <button className="run-query" onClick={() => void runQuery()} disabled={running}>
                    {running ? 'Running…' : 'Run query'}
                </button>
            </header>

            <div className="workspace">
                <nav className="sidebar">
                    <a
                        className={activePage === 'explore' ? 'nav-link active' : 'nav-link'}
                        href="#explore"
                        onClick={() => setActivePage('explore')}
                    >Explore</a>
                    <a
                        className={activePage === 'mapping' ? 'nav-link active' : 'nav-link'}
                        href="#mapping"
                        onClick={() => setActivePage('mapping')}
                    >Ontology Mapping</a>
                    <a
                        className={activePage === 'legacy-fibo' ? 'nav-link active' : 'nav-link'}
                        href="#legacy-fibo"
                        onClick={() => setActivePage('legacy-fibo')}
                    >Legacy → FIBO</a>
                    <a
                        className={activePage === 'sql-lineage' ? 'nav-link active' : 'nav-link'}
                        href="#sql-lineage"
                        onClick={() => setActivePage('sql-lineage')}
                    >SQL Lineage</a>
                    <a
                        className={activePage === 'sql-lineage-owl' ? 'nav-link active' : 'nav-link'}
                        href="#sql-lineage-owl"
                        onClick={() => setActivePage('sql-lineage-owl')}
                    >SQL Lineage OWL</a>
                    <a className="nav-link" href="#govern">Govern</a>
                    <a className="nav-link" href="#chat">Chat</a>
                    <a className="nav-link" href="#admin">Admin</a>
                </nav>

                <main className="content">
                    {activePage === 'mapping'
                        ? <OntologyMapping />
                        : activePage === 'legacy-fibo'
                            ? <LegacyFiboMapping />
                            : activePage === 'sql-lineage'
                                ? <SqlLineage />
                                : activePage === 'sql-lineage-owl'
                                    ? <SqlLineageOwl />
                            : <>
                    <div className="content-heading">
                        <h1>Explore</h1>
                        <label className="borrower-select">
                            Borrower
                            <select
                                value={selectedBorrowerId}
                                onChange={(event) => {
                                    const borrowerId = event.target.value
                                    setBorrowerProfileLoading(Boolean(borrowerId))
                                    void loadBorrowerProfile(borrowerId, {
                                        onBorrowerChange: setSelectedBorrowerId,
                                        onProfileChange: setBorrowerProfile,
                                        onError: setError,
                                    }).finally(() => setBorrowerProfileLoading(false))
                                }}
                            >
                                <option value="" disabled={borrowersLoading}>
                                    {borrowersLoading ? 'Loading borrowers…' : 'Choose a borrower'}
                                </option>
                                {borrowers.map((borrower) => (
                                    <option key={borrower.borrowerId} value={borrower.borrowerId}>
                                        {borrower.borrowerName} ({borrower.borrowerId})
                                    </option>
                                ))}
                            </select>
                        </label>
                        {borrowersLoading && (
                            <span className="loading-indicator" role="status">
                                <span className="loading-spinner" aria-hidden="true" />
                                Loading borrowers
                            </span>
                        )}
                    </div>
                    {error && <pre className="error-output">{error}</pre>}
                    <div className="panes">
                        <section className="pane result-pane">
                            <h2>Cypher result</h2>
                            {borrowerProfileLoading ? (
                                <div className="loading-indicator" role="status">
                                    <span className="loading-spinner" aria-hidden="true" />
                                    Loading borrower profile
                                </div>
                            ) : borrowerProfile ? <BorrowerProfile profile={borrowerProfile} /> : null}
                            <pre className="result-output">
                                {result !== null
                                    ? JSON.stringify(result, null, 2)
                                    : borrowerProfile
                                        ? ''
                                        : 'Run a Cypher query or select a borrower to see returned data.'}
                            </pre>
                        </section>

                        <section className="pane saved-pane">
                            <div className="save-query-form">
                                <input
                                    aria-label="Saved query name"
                                    placeholder="Query name"
                                    value={queryName}
                                    onChange={(event) => setQueryName(event.target.value)}
                                />
                                <button
                                    onClick={() => void saveQuery()}
                                    disabled={!query.trim() || !queryName.trim()}
                                >
                                    Save
                                </button>
                            </div>
                            <div className="saved-query-list">
                                {savedQueriesLoading ? (
                                    <div className="loading-indicator" role="status">
                                        <span className="loading-spinner" aria-hidden="true" />
                                        Loading saved queries
                                    </div>
                                ) : savedQueries.map((saved) => (
                                    <button
                                        className="saved-query-name"
                                        key={saved.id}
                                        onClick={() => setQuery(saved.cypher)}
                                        title={saved.cypher}
                                    >
                                        {saved.name}
                                    </button>
                                ))}
                            </div>
                        </section>
                    </div>
                            </>}
                </main>
            </div>
        </div>
    )
}

export default App

import type { BorrowerProfileData } from '../BorrowerProfile'

export type SavedQuery = {
    id: number
    name: string
    cypher: string
    created_at: string
}

type BorrowerProfileResponse = {
    borrower: BorrowerProfileData
}

type LoadBorrowerProfileCallbacks = {
    onBorrowerChange: (borrowerId: string) => void
    onProfileChange: (profile: BorrowerProfileData | null) => void
    onError: (message: string) => void
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''



export async function loadSavedQueries(): Promise<SavedQuery[]> {
    const response = await fetch(`${API_BASE}/neo4j/saved-queries`)
    if (!response.ok) throw new Error(await response.text())
    return await response.json() as SavedQuery[]
}



export async function loadBorrowerProfile(
    borrowerId: string,
    { onBorrowerChange, onProfileChange, onError }: LoadBorrowerProfileCallbacks,
): Promise<void> {
    onBorrowerChange(borrowerId)
    onProfileChange(null)
    onError('')
    if (!borrowerId) return

    try {
        const response = await fetch(
            `${API_BASE}/loan/borrowers/${encodeURIComponent(borrowerId)}`,
        )
        if (!response.ok) throw new Error(await response.text())

        const rows = await response.json() as BorrowerProfileResponse[]
        onProfileChange(rows[0]?.borrower ?? null)
    } catch (cause) {
        onError(cause instanceof Error ? cause.message : String(cause))
    }
}


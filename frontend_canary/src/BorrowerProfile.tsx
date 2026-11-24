import RelationshipExplorer from './RelationshipExplorer'

export type BorrowerLoan = {
    loanId: string
    borrowerRole: string
    status: string
    principalAmount: number
    currentBalance: number
    interestRate: number
    originationDate: string
    maturityDate: string
}

export type BorrowerProfileData = {
    borrowerId: string
    borrowerName: string
    loans: BorrowerLoan[]
}

type Props = {
    profile: BorrowerProfileData | null
}

export default function BorrowerProfile({ profile }: Props) {
    if (!profile) {
        return <p>Select a borrower to view their profile.</p>
    }

    return (
        <section className="borrower-profile">
            <h2>{profile.borrowerName}</h2>
            <p>Borrower ID: {profile.borrowerId}</p>
            <RelationshipExplorer
                nodeLabel="Person"
                idProperty="personId"
                nodeId={profile.borrowerId}
                displayName={profile.borrowerName}
            />

            <h3>Loans ({profile.loans.length})</h3>
            {profile.loans.length === 0 ? (
                <p>No loans found.</p>
            ) : (
                <ul>
                    {profile.loans.map((loan) => (
                        <li key={loan.loanId}>
                            <strong>{loan.loanId}</strong> · {loan.status}
                            <div>Role: {loan.borrowerRole}</div>
                            <div>Balance: {loan.currentBalance}</div>
                            <div>Principal: {loan.principalAmount}</div>
                            <div>Interest rate: {loan.interestRate}%</div>
                            <div>Origination: {loan.originationDate}</div>
                            <div>Maturity: {loan.maturityDate}</div>
                            <RelationshipExplorer
                                nodeLabel="Loan"
                                idProperty="loanId"
                                nodeId={loan.loanId}
                                displayName={loan.loanId}
                            />
                        </li>
                    ))}
                </ul>
            )}
        </section>
    )
}

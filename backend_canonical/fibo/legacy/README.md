# Legacy Loan Mapping Demo

All records are fictional. This package is designed for a source-to-ontology mapping demo.

## Files
- `legacy_loan_demo.sql`: PostgreSQL DDL and INSERT statements.
- `data_dictionary.json`: table descriptions and starter mapping candidates.

## Load
Run `legacy_loan_demo.sql` against a disposable PostgreSQL database.

## Suggested demo flow
1. Introspect source tables and columns from PostgreSQL metadata.
2. Display source objects in the Ontology Mapping UI.
3. Search/select target FIBO or enterprise ontology classes/properties.
4. Save mapping records in a separate Mapping Registry.
5. Review/approve mappings.
6. Later, associate SQL-derived lineage with the mapped source fields.

## Important
The abbreviated source names are intentional (`LN_ACCT`, `CUST_MST`, `OUT_BAL`, etc.).
The dataset is synthetic and should be labelled as such in any demo.

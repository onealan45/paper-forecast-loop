# Role: Data

## Mission
Own data ingestion, transformation, integrity, and schema consistency.

## Best for
- ETL
- provider adapters
- dataset validation
- schema drift handling

## Should do
- validate source assumptions
- make transformations explicit
- protect against silent null / gap / type issues
- produce integrity checks

## Should not do
- bury business logic in ingestion layers
- treat partial data as complete without flags
- conflate raw and derived fields carelessly

## Inputs needed
- source schema
- cadence / freshness rules
- downstream consumers

## Outputs
- reliable ingestion / transform logic
- data validation checks
- schema notes

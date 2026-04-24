# Role: Contract

## Mission
Protect schema meaning, provenance, and stable identity semantics.

## Best for
- artifact design
- version fields
- provenance improvements
- backward compatibility
- identity / hashing rules

## Should do
- clarify what each field means
- keep schema changes explicit
- add versioning when semantics may evolve
- preserve backward compatibility unless intentionally broken

## Should not do
- change semantics silently
- overload fields with multiple meanings
- ignore migration impact

## Inputs needed
- current models / schemas
- desired semantics
- compatibility requirements

## Outputs
- schema updates
- version / provenance policy
- migration or compatibility note

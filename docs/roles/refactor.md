# Role: Refactor

## Mission
Improve structure while preserving behavior.

## Best for
- extracting modules
- removing duplication
- simplifying flow
- clarifying boundaries

## Should do
- preserve external behavior unless explicitly approved otherwise
- keep changes mechanically understandable
- pair with strong regression tests
- surface compatibility risk early

## Should not do
- mix refactor and feature invention casually
- hide semantic changes inside cleanup
- rewrite large areas without migration reasoning

## Inputs needed
- target structure
- preserved behaviors
- affected modules

## Outputs
- structural improvement
- preserved behavior evidence
- concise migration / compatibility note

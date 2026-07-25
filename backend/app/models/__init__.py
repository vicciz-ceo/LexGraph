"""ORM model package. Empty on purpose (R2): no model classes are defined
yet. Developer tracks register SQLAlchemy model classes against
`app.db.Base` here (or in submodules imported from here) per the "Data
model reference" section of the sprint contract. Tests never import model
classes directly (that would be an import-error RED, which is disallowed
for backend tests) — they go through the real HTTP API or raw SQL against
the documented table/column names.
"""

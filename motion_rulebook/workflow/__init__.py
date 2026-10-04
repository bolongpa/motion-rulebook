"""Automated rule-mining workflow.

Stages (each writes files for human review):
    corpus    user-submitted panels: image + event + artist + source
    describe  VLM documents observable depiction elements per panel
    mine      consensus across instances -> candidate rules
    ground    official-source provenance only (allowlist enforced)

Mining never writes final rules: it outputs *candidates* with support
counts. A human promotes candidates into a rulebook.
"""

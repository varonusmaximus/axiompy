# @!tooling

"""
AxiomPy CLI entry-points.

Thin wrappers kept isolated from the main ``axiompy`` library so that
``import axiompy`` never pays for argparse/shutil unless a CLI is invoked.
"""

"""A2UI v0.9 integration for the agent.

Rather than separate tools that deterministically build and return a
surface, the agent's own LLM is prompted to emit A2UI JSON directly in its
response when the user wants to create an item or view item details (the
"direct JSON" inference format the A2UI processor is built around). This
module builds the A2uiRequestProcessor (a2ui.processor) that makes that
possible:

- Its prompt_snippet carries the catalog's JSON schema plus a few-shot
  example per surface, each loaded from a literal JSON surface/component
  definition in ../a2ui/surfaces/ (not constructed in Python) and validated
  against the catalog with a2ui.parser.normalize_prompt_example_messages.
- Its parse_response validates whatever A2UI JSON the LLM actually produces
  against that same schema.

Surfaces defined:

- "item_creation" (item_creation.json): a form with every field needed to
  create an item.
- "item_table" (item_table.json): a table of item details, with one row per
  item in the /items data-model path, which the agent populates from the
  item-mcp list_items tool's results.
"""

from __future__ import annotations

import json
from pathlib import Path

from a2ui.core.basic_catalog import BasicCatalog
from a2ui.parser import normalize_prompt_example_messages
from a2ui.processor import A2uiGenerator, A2uiRequestProcessor, CatalogConfig
from a2ui.schema import VERSION_0_9

A2UI_DIR = Path(__file__).resolve().parent.parent / "agent" / "a2ui"
PROTOCOL_VERSION = f"v{VERSION_0_9}"

# (surface file name, surfaceId) for every surface the agent has a few-shot
# example for. Each becomes its own <a2ui-json> example block in the prompt.
SURFACE_EXAMPLES = [
    ("item_creation", "item_creation"),
    ("item_table", "item_table"),
]


def _load_example(filename: str, surface_id: str, catalog_id: str):
    surface_json = json.loads((A2UI_DIR / "surfaces" / f"{filename}.json").read_text())
    return normalize_prompt_example_messages(
        surface_json,
        version=PROTOCOL_VERSION,
        default_catalog_id=catalog_id,
        default_surface_id=surface_id,
    )


def build_processor() -> A2uiRequestProcessor:
    """Builds the A2uiRequestProcessor the agent renders A2UI content
    against: the basic v0.9 catalog, negotiated the same way a real
    renderer's capabilities would be, primed with one validated few-shot
    example per surface (see SURFACE_EXAMPLES) so the LLM has a concrete,
    schema-correct shape to follow for each.
    """
    catalog = BasicCatalog(VERSION_0_9)

    examples = [
        _load_example(filename, surface_id, catalog.catalog_id)
        for filename, surface_id in SURFACE_EXAMPLES
    ]

    generator = A2uiGenerator([CatalogConfig(catalog)], examples=examples)
    return generator.create_processor({
        PROTOCOL_VERSION: {
            "supportedCatalogIds": [c.transformed_catalog.catalog_id for c in generator.catalogs]
        }
    })

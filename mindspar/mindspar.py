"""Mindspar (腦力擂台): a quiz duel against the AI the AI Hub sets for this app."""

import reflex as rx
from reflex_ddns_auth import ai

from mindspar import opponent
from mindspar.state import Game
from mindspar.views import index

app = rx.App()
app.add_page(index, route="/", title="Mindspar · 腦力擂台", on_load=Game.on_load)

# The AI Hub's page lists this app's AI by these words, with the model each answers with.
ai.uses(app, **opponent.USES)

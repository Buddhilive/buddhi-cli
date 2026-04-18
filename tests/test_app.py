import pytest
from buddhi_ai_server.app import BuddhiAIApp

@pytest.mark.asyncio
async def test_hello_world_rendered():
    """A basic test to inspect our textual app."""
    app = BuddhiAIApp()
    async with app.run_test() as pilot:
        # Check if the text exists in the label
        label = app.query_one("#hello-label")
        assert "Hello World!" in str(label.render())

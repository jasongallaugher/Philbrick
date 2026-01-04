"""Tests for AnalogApp TUI application."""

import pytest
from main import AnalogApp


@pytest.mark.asyncio
async def test_toggle_run_action() -> None:
    """Space key toggles run/pause state."""
    app = AnalogApp()
    async with app.run_test() as pilot:
        # App starts paused
        assert app.running is False
        
        # Press space to start
        await pilot.press("space")
        assert app.running is True
        
        # Press space again to pause
        await pilot.press("space")
        assert app.running is False


@pytest.mark.asyncio
async def test_reset_action() -> None:
    """R key resets simulation and stops running."""
    app = AnalogApp()
    async with app.run_test() as pilot:
        # Start running
        await pilot.press("space")
        assert app.running is True
        
        # Advance time a bit
        initial_time = app.machine.time
        for _ in range(10):
            app.simulation_step()
        assert app.machine.time > initial_time
        
        # Reset should stop and reset time
        await pilot.press("r")
        assert app.running is False
        assert app.machine.time == 0.0
        assert len(app.scope.samples) == 0


@pytest.mark.asyncio
async def test_quit_action() -> None:
    """Q key quits the application."""
    app = AnalogApp()
    async with app.run_test() as pilot:
        # App should be running
        assert app.is_running is True
        
        # Press q to quit
        await pilot.press("q")
        
        # App should exit
        assert app.is_running is False


@pytest.mark.asyncio
async def test_bindings_defined() -> None:
    """App has required keyboard bindings."""
    app = AnalogApp()
    
    # Check bindings exist
    assert len(app.BINDINGS) >= 3
    
    # Check specific bindings
    binding_keys = {binding.key for binding in app.BINDINGS}
    assert "space" in binding_keys
    assert "r" in binding_keys
    assert "q" in binding_keys



from talon import Module, actions
from .ui.app import parrot_tester_toggle

mod = Module()
mod.tag("parrot_tester", "mode for testing parrot")

@mod.action_class
class Actions:
    def parrot_tester_toggle():
        """Toggle parrot tester"""
        parrot_tester_toggle()

    def parrot_tester_integration_ready():
        """Overrides with True when hook is created/ready"""
        return False

    def parrot_tester_wrap_parrot_integration():
        """Wrap parrot_integration file for introspection - Automatically overwritten by context"""
        actions.skip()

    def parrot_tester_restore_parrot_integration(reset_ui_state: bool = True):
        """Restore parrot_integration file - Automatically overwritten by context"""
        actions.skip()
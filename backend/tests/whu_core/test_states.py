import pytest

from whu_core.states import ExecutionState, can_transition, require_transition


@pytest.mark.parametrize("terminal", [
    ExecutionState.COMPLETED,
    ExecutionState.ERROR,
    ExecutionState.CANCELLED,
])
def test_terminal_states_have_no_outbound_transition(terminal):
    for candidate in ExecutionState:
        assert can_transition(terminal, candidate) is False


def test_expected_lifecycle_is_legal():
    require_transition(ExecutionState.PENDING, ExecutionState.RUNNING)
    require_transition(ExecutionState.RUNNING, ExecutionState.COMPLETED)


def test_error_cannot_become_pass_equivalent():
    with pytest.raises(ValueError, match="ERROR -> COMPLETED"):
        require_transition(ExecutionState.ERROR, ExecutionState.COMPLETED)

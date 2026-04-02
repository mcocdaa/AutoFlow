import pytest

from app.runtime.nodes import RetryNode


def test_retry_node_initialization():
    node = RetryNode(id="retry1", name="Test Retry")
    assert node.id == "retry1"
    assert node.name == "Test Retry"
    assert node.type == "retry"
    assert len(node.inputs) == 1
    assert node.inputs[0].id == "input"
    assert len(node.outputs) == 1
    assert node.outputs[0].id == "output"
    assert node.attempts == 0
    assert node.backoff_seconds == 0.0


def test_retry_node_config():
    node = RetryNode(id="retry1", config={"attempts": 3, "backoff_seconds": 2.0})
    assert node.attempts == 3
    assert node.backoff_seconds == 2.0


def test_retry_node_success_first_try():
    node = RetryNode(id="retry1", config={"attempts": 3})

    def success_handler(x):
        return x * 2

    result = node.execute({"input": 5}, action_handler=success_handler)
    assert result["output"] == 10


def test_retry_node_eventually_succeeds():
    attempt_count = 0

    def flaky_handler(x):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception("Failed")
        return x * 2

    node = RetryNode(id="retry1", config={"attempts": 3})

    result = node.execute({"input": 5}, action_handler=flaky_handler)
    assert result["output"] == 10
    assert attempt_count == 3


def test_retry_node_all_attempts_fail():
    fail_count = 0

    def always_fail(x):
        nonlocal fail_count
        fail_count += 1
        raise Exception("Always fails")

    node = RetryNode(id="retry1", config={"attempts": 2})

    with pytest.raises(Exception, match="Always fails"):
        node.execute({"input": 5}, action_handler=always_fail)
    assert fail_count == 3


def test_retry_node_exponential_backoff():
    wait_times = []

    def record_sleep(t):
        wait_times.append(t)

    def always_fail(x):
        raise Exception("Failed")

    node = RetryNode(id="retry1", config={"attempts": 2, "backoff_seconds": 1.0})

    with pytest.raises(Exception, match="Failed"):
        node.execute({"input": 5}, action_handler=always_fail, sleep_func=record_sleep)
    assert wait_times == [1.0, 2.0]


def test_retry_node_no_handler():
    node = RetryNode(id="retry1")

    result = node.execute({"input": "test"})
    assert result["output"] == "test"

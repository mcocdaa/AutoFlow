from unittest.mock import AsyncMock, MagicMock

import pytest

from app.runtime.websocket_manager import WebSocketManager, get_websocket_manager


@pytest.fixture(autouse=True)
def reset_websocket_manager():
    """在每个测试前重置 WebSocketManager 单例状态"""
    manager = WebSocketManager()
    manager._connections.clear()
    manager._subscriptions.clear()
    yield
    manager._connections.clear()
    manager._subscriptions.clear()


class TestWebSocketManagerSingleton:
    def test_singleton_instance(self):
        """测试 WebSocketManager 是单例模式"""
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()
        assert manager1 is manager2

    def test_new_instance_not_same(self):
        """测试直接实例化也返回同一个实例"""
        manager1 = WebSocketManager()
        manager2 = WebSocketManager()
        assert manager1 is manager2


class TestWebSocketManagerConnection:
    def test_register_connection(self):
        """测试注册连接"""
        manager = WebSocketManager()
        websocket = MagicMock()
        conn_id = "test-connection-id"

        manager.register_connection(conn_id, websocket)

        assert conn_id in manager._connections
        assert manager._connections[conn_id] is websocket

    def test_unregister_connection(self):
        """测试取消注册连接"""
        manager = WebSocketManager()
        websocket = MagicMock()
        conn_id = "test-connection-id"

        manager.register_connection(conn_id, websocket)
        manager.unregister_connection(conn_id)

        assert conn_id not in manager._connections

    def test_unregister_nonexistent_connection(self):
        """测试取消注册不存在的连接不会报错"""
        manager = WebSocketManager()

        try:
            manager.unregister_connection("nonexistent-connection")
        except Exception as e:
            pytest.fail(f"unregister_connection raised {type(e).__name__} unexpectedly")


class TestWebSocketManagerSubscription:
    def test_subscribe(self):
        """测试订阅"""
        manager = WebSocketManager()
        conn_id = "test-connection"
        run_id = "test-run"

        manager.subscribe(conn_id, run_id)

        assert run_id in manager._subscriptions
        assert conn_id in manager._subscriptions[run_id]

    def test_unsubscribe(self):
        """测试取消订阅"""
        manager = WebSocketManager()
        conn_id = "test-connection"
        run_id = "test-run"

        manager.subscribe(conn_id, run_id)
        manager.unsubscribe(conn_id, run_id)

        assert run_id not in manager._subscriptions

    def test_unsubscribe_nonexistent_run(self):
        """测试取消订阅不存在的执行不会报错"""
        manager = WebSocketManager()
        conn_id = "test-connection"

        try:
            manager.unsubscribe(conn_id, "nonexistent-run")
        except Exception as e:
            pytest.fail(f"unsubscribe raised {type(e).__name__} unexpectedly")

    def test_unsubscribe_nonexistent_connection(self):
        """测试取消订阅不存在的连接不会报错"""
        manager = WebSocketManager()
        run_id = "test-run"

        try:
            manager.unsubscribe("nonexistent-connection", run_id)
        except Exception as e:
            pytest.fail(f"unsubscribe raised {type(e).__name__} unexpectedly")

    def test_multiple_subscriptions_same_run(self):
        """测试多个连接订阅同一个执行"""
        manager = WebSocketManager()

        manager.subscribe("conn1", "run1")
        manager.subscribe("conn2", "run1")

        assert "run1" in manager._subscriptions
        assert len(manager._subscriptions["run1"]) == 2
        assert "conn1" in manager._subscriptions["run1"]
        assert "conn2" in manager._subscriptions["run1"]

    def test_unregister_cleans_up_subscriptions(self):
        """测试取消注册连接时会清理相关订阅"""
        manager = WebSocketManager()
        conn_id = "test-connection"
        run_id1 = "test-run-1"
        run_id2 = "test-run-2"

        manager.subscribe(conn_id, run_id1)
        manager.subscribe(conn_id, run_id2)
        manager.unregister_connection(conn_id)

        assert run_id1 not in manager._subscriptions
        assert run_id2 not in manager._subscriptions


class TestWebSocketManagerBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_event(self):
        """测试广播事件"""
        manager = WebSocketManager()
        conn_id = "test-connection"
        run_id = "test-run"

        websocket = MagicMock()
        websocket.send_json = AsyncMock()

        manager.register_connection(conn_id, websocket)
        manager.subscribe(conn_id, run_id)

        event_data = {"type": "test_event", "data": "test"}
        await manager.broadcast_event(run_id, event_data)

        websocket.send_json.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_broadcast_no_subscribers(self):
        """测试没有订阅者时广播不会报错"""
        manager = WebSocketManager()

        try:
            await manager.broadcast_event("nonexistent-run", {"type": "test"})
        except Exception as e:
            pytest.fail(f"broadcast_event raised {type(e).__name__} unexpectedly")

    @pytest.mark.asyncio
    async def test_broadcast_multiple_subscribers(self):
        """测试向多个订阅者广播"""
        manager = WebSocketManager()
        run_id = "test-run"

        websocket1 = MagicMock()
        websocket1.send_json = AsyncMock()
        manager.register_connection("conn1", websocket1)
        manager.subscribe("conn1", run_id)

        websocket2 = MagicMock()
        websocket2.send_json = AsyncMock()
        manager.register_connection("conn2", websocket2)
        manager.subscribe("conn2", run_id)

        event_data = {"type": "test_event"}
        await manager.broadcast_event(run_id, event_data)

        websocket1.send_json.assert_called_once_with(event_data)
        websocket2.send_json.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnect(self):
        """测试广播时处理断开连接的情况"""
        manager = WebSocketManager()
        conn_id = "test-connection"
        run_id = "test-run"

        websocket = MagicMock()
        websocket.send_json = AsyncMock(side_effect=Exception("Disconnected"))

        manager.register_connection(conn_id, websocket)
        manager.subscribe(conn_id, run_id)

        try:
            await manager.broadcast_event(run_id, {"type": "test"})
        except Exception as e:
            pytest.fail(f"broadcast_event raised {type(e).__name__} unexpectedly")

        assert conn_id not in manager._connections
        assert run_id not in manager._subscriptions

    @pytest.mark.asyncio
    async def test_broadcast_unregistered_connection(self):
        """测试向已取消注册的连接广播"""
        manager = WebSocketManager()
        conn_id = "test-connection"
        run_id = "test-run"

        manager.subscribe(conn_id, run_id)

        try:
            await manager.broadcast_event(run_id, {"type": "test"})
        except Exception as e:
            pytest.fail(f"broadcast_event raised {type(e).__name__} unexpectedly")

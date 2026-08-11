# @file /backend/tests/test_serialization.py
# @brief app.runtime.utils.serialization 单元测试:safe_deep_copy / to_jsonable
# @create 2026-08-10

from __future__ import annotations

from app.runtime.utils.serialization import safe_deep_copy, to_jsonable


class TestSafeDeepCopy:
    def test_deep_copies_nested_dict(self) -> None:
        source = {"a": [1, 2, {"b": 3}]}
        result = safe_deep_copy(source)
        assert result == source
        result["a"][2]["b"] = 99
        assert source["a"][2]["b"] == 3

    def test_handles_self_referencing_list(self) -> None:
        value = [1, 2]
        value.append(value)
        result = safe_deep_copy(value)
        assert result[:2] == [1, 2]
        assert result[2] is result

    def test_handles_shared_references(self) -> None:
        shared = {"x": 1}
        value = {"a": shared, "b": shared}
        result = safe_deep_copy(value)
        assert result["a"] == result["b"] == {"x": 1}
        assert result["a"] is result["b"]

    def test_primitives_returned_as_is(self) -> None:
        assert safe_deep_copy(None) is None
        assert safe_deep_copy(1) == 1
        assert safe_deep_copy("s") == "s"
        assert safe_deep_copy(True) is True

    def test_uncopyable_falls_back_to_str(self) -> None:
        class Uncopyable:
            def __str__(self) -> str:
                return "<uncopyable>"

            def __deepcopy__(self, memo):
                raise TypeError("boom")

        result = safe_deep_copy({"obj": Uncopyable()})
        assert result == {"obj": "<uncopyable>"}


class TestToJsonable:
    def test_passthrough_dict(self) -> None:
        assert to_jsonable({"a": 1, "b": [True, None]}) == {"a": 1, "b": [True, None]}

    def test_non_serializable_uses_default_str(self) -> None:
        class Obj:
            def __str__(self) -> str:
                return "<obj>"

        result = to_jsonable({"obj": Obj(), "n": 1})
        assert result == {"obj": "<obj>", "n": 1}

    def test_circular_reference_returns_str_fallback(self) -> None:
        value = {"name": "x"}
        value["self"] = value
        result = to_jsonable(value)
        assert isinstance(result, str)
        assert "x" in result

    def test_string_fallback_when_dumps_fails(self) -> None:
        class BrokenStr:
            def __str__(self) -> str:
                raise ValueError("no str")

        result = to_jsonable({"x": BrokenStr()})
        assert isinstance(result, str)

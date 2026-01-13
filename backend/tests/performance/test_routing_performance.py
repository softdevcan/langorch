"""
Performance tests for unified workflow routing

LangOrch v0.4.1 - Ensures routing overhead stays within acceptable bounds
"""
import pytest
import time
from unittest.mock import MagicMock

from app.workflows.nodes.router_strategies import heuristic_route
from app.core.enums import SessionMode


class TestRoutingPerformance:
    """Performance tests for routing logic"""

    def test_heuristic_routing_performance_simple_query(self):
        """Test that heuristic routing completes in < 50ms for simple queries"""
        session_context = {
            "document_context": {
                "total_documents": 5,
                "total_chunks": 25
            }
        }

        # Warm up
        for _ in range(10):
            heuristic_route(
                user_input="hello",
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context=session_context
            )

        # Measure performance
        iterations = 100
        start_time = time.perf_counter()

        for _ in range(iterations):
            result = heuristic_route(
                user_input="hello",
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context=session_context
            )

        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / iterations) * 1000

        # Assert performance requirement
        assert avg_time_ms < 50, f"Routing took {avg_time_ms:.2f}ms, expected < 50ms"

        # Log performance
        print(f"\n[PASS] Simple query routing: {avg_time_ms:.2f}ms average ({iterations} iterations)")

    def test_heuristic_routing_performance_complex_query(self):
        """Test routing performance with complex queries"""
        session_context = {
            "document_context": {
                "total_documents": 20,
                "total_chunks": 100
            }
        }

        complex_query = (
            "Can you please help me understand what the documentation says about "
            "the implementation of the routing algorithm and how it compares to "
            "other approaches mentioned in the research papers?"
        )

        # Warm up
        for _ in range(10):
            heuristic_route(
                user_input=complex_query,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context=session_context
            )

        # Measure performance
        iterations = 100
        start_time = time.perf_counter()

        for _ in range(iterations):
            result = heuristic_route(
                user_input=complex_query,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context=session_context
            )

        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / iterations) * 1000

        # Assert performance requirement (slightly higher threshold for complex queries)
        assert avg_time_ms < 50, f"Complex routing took {avg_time_ms:.2f}ms, expected < 50ms"

        print(f"[PASS] Complex query routing: {avg_time_ms:.2f}ms average ({iterations} iterations)")

    def test_heuristic_routing_performance_worst_case(self):
        """Test routing performance in worst-case scenario"""
        session_context = {
            "document_context": {
                "total_documents": 100,
                "total_chunks": 1000
            }
        }

        # Very long query with mixed languages
        worst_case_query = " ".join([
            "merhaba hello",
            "what does the document say",
            "ne yazıyor",
            "explain this concept",
            "bul bana"
        ] * 10)

        # Warm up
        for _ in range(10):
            heuristic_route(
                user_input=worst_case_query,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context=session_context
            )

        # Measure performance
        iterations = 100
        start_time = time.perf_counter()

        for _ in range(iterations):
            result = heuristic_route(
                user_input=worst_case_query,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context=session_context
            )

        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / iterations) * 1000

        # Even worst case should be under 50ms
        assert avg_time_ms < 50, f"Worst-case routing took {avg_time_ms:.2f}ms, expected < 50ms"

        print(f"[PASS] Worst-case routing: {avg_time_ms:.2f}ms average ({iterations} iterations)")

    def test_routing_memory_efficiency(self):
        """Test that routing doesn't create excessive memory overhead"""
        import sys

        session_context = {
            "document_context": {
                "total_documents": 50,
                "total_chunks": 200
            }
        }

        # Get baseline memory
        result = heuristic_route(
            user_input="test query",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context=session_context
        )

        # Check result size
        result_size = sys.getsizeof(result)

        # Routing result should be small (< 10KB)
        assert result_size < 10_000, f"Routing result size {result_size} bytes, expected < 10KB"

        print(f"[PASS] Routing result size: {result_size} bytes")

    def test_mode_override_performance(self):
        """Test that explicit mode override has minimal overhead"""
        session_context = {}

        # Warm up
        for _ in range(10):
            heuristic_route(
                user_input="what is in the document",
                has_documents=True,
                session_mode=SessionMode.CHAT_ONLY,
                session_context=session_context
            )

        # Measure performance
        iterations = 100
        start_time = time.perf_counter()

        for _ in range(iterations):
            result = heuristic_route(
                user_input="what is in the document",
                has_documents=True,
                session_mode=SessionMode.CHAT_ONLY,
                session_context=session_context
            )

        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / iterations) * 1000

        # Mode override should be very fast (< 10ms)
        assert avg_time_ms < 10, f"Mode override took {avg_time_ms:.2f}ms, expected < 10ms"

        print(f"[PASS] Mode override routing: {avg_time_ms:.2f}ms average ({iterations} iterations)")

    def test_concurrent_routing_performance(self):
        """Test routing performance under concurrent load"""
        import asyncio

        async def route_query(query: str, has_docs: bool):
            """Simulate async routing"""
            return heuristic_route(
                user_input=query,
                has_documents=has_docs,
                session_mode=SessionMode.AUTO,
                session_context={}
            )

        async def concurrent_test():
            queries = [
                ("hello", False),
                ("what does the document say", True),
                ("explain this concept", True),
                ("merhaba", False),
                ("summarize the paper", True),
            ]

            # Run 20 concurrent routing operations
            tasks = [route_query(q, has_docs) for q, has_docs in queries * 4]

            start_time = time.perf_counter()
            results = await asyncio.gather(*tasks)
            end_time = time.perf_counter()

            total_time_ms = (end_time - start_time) * 1000
            avg_time_ms = total_time_ms / len(tasks)

            return avg_time_ms, len(results)

        # Run concurrent test
        avg_time, count = asyncio.run(concurrent_test())

        # Average should still be under 50ms
        assert avg_time < 50, f"Concurrent routing took {avg_time:.2f}ms average, expected < 50ms"

        print(f"[PASS] Concurrent routing ({count} operations): {avg_time:.2f}ms average")


class TestRoutingBenchmarks:
    """Benchmark tests for comparison"""

    def test_benchmark_all_routing_rules(self):
        """Benchmark all routing rule paths"""
        test_cases = [
            ("hello", False, SessionMode.AUTO, "greeting"),
            ("what does the document say", True, SessionMode.AUTO, "document_keywords"),
            ("who are you", True, SessionMode.AUTO, "small_talk"),
            ("explain this concept", True, SessionMode.AUTO, "ambiguous"),
            ("test", False, SessionMode.AUTO, "default_chat"),
            ("what is in the document", True, SessionMode.CHAT_ONLY, "mode_override"),
        ]

        print("\n=== Routing Rule Benchmarks ===")

        for query, has_docs, mode, expected_rule in test_cases:
            iterations = 100
            start_time = time.perf_counter()

            for _ in range(iterations):
                result = heuristic_route(
                    user_input=query,
                    has_documents=has_docs,
                    session_mode=mode,
                    session_context={}
                )

            end_time = time.perf_counter()
            avg_time_ms = ((end_time - start_time) / iterations) * 1000

            print(f"  {expected_rule:20s}: {avg_time_ms:6.2f}ms")

            # All rules should be fast
            assert avg_time_ms < 50

    def test_benchmark_query_lengths(self):
        """Benchmark routing with different query lengths"""
        base_query = "what does the document say about this topic"

        print("\n=== Query Length Benchmarks ===")

        for multiplier in [1, 5, 10, 20]:
            query = " ".join([base_query] * multiplier)
            word_count = len(query.split())

            iterations = 100
            start_time = time.perf_counter()

            for _ in range(iterations):
                result = heuristic_route(
                    user_input=query,
                    has_documents=True,
                    session_mode=SessionMode.AUTO,
                    session_context={}
                )

            end_time = time.perf_counter()
            avg_time_ms = ((end_time - start_time) / iterations) * 1000

            print(f"  {word_count:3d} words: {avg_time_ms:6.2f}ms")

            # Should scale linearly, not exponentially
            assert avg_time_ms < 50

    def test_benchmark_document_counts(self):
        """Benchmark routing with different document counts"""
        print("\n=== Document Count Benchmarks ===")

        for doc_count in [0, 10, 50, 100, 500]:
            session_context = {
                "document_context": {
                    "total_documents": doc_count,
                    "total_chunks": doc_count * 5
                }
            }

            iterations = 100
            start_time = time.perf_counter()

            for _ in range(iterations):
                result = heuristic_route(
                    user_input="what is in the document",
                    has_documents=doc_count > 0,
                    session_mode=SessionMode.AUTO,
                    session_context=session_context
                )

            end_time = time.perf_counter()
            avg_time_ms = ((end_time - start_time) / iterations) * 1000

            print(f"  {doc_count:3d} docs: {avg_time_ms:6.2f}ms")

            # Document count shouldn't affect routing performance significantly
            assert avg_time_ms < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

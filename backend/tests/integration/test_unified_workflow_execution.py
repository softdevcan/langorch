"""
Integration tests for unified workflow execution

LangOrch v0.4.1 - Tests workflow routing and API integration

These tests focus on:
1. Routing logic integration with session/document context
2. API endpoint backward compatibility
3. Response structure validation
"""
import pytest

from app.workflows.nodes.router_strategies import heuristic_route
from app.core.enums import SessionMode


@pytest.mark.asyncio
class TestUnifiedWorkflowRoutingIntegration:
    """Integration tests for workflow routing with session context"""

    async def test_routing_with_empty_session_context(self):
        """Test routing works with minimal session context"""
        result = heuristic_route(
            user_input="hello",
            has_documents=False,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        assert result["route"] == "direct_chat"
        assert "reasoning" in result
        assert 0.0 <= result["confidence"] <= 1.0

    async def test_routing_with_full_session_context(self):
        """Test routing with complete session context"""
        session_context = {
            "document_context": {
                "total_documents": 5,
                "total_chunks": 25,
                "last_updated": "2024-01-01T00:00:00Z"
            },
            "session_metadata": {
                "user_preferences": {"language": "en"},
                "last_query_type": "rag"
            }
        }

        result = heuristic_route(
            user_input="what does the document say about AI",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context=session_context
        )

        assert result["route"] == "rag_needed"
        assert result["reasoning"]["total_documents"] == 5

    async def test_routing_mode_override_integration(self):
        """Test that session mode properly overrides routing logic"""
        # Test CHAT_ONLY mode
        result_chat = heuristic_route(
            user_input="what is in the document",
            has_documents=True,
            session_mode=SessionMode.CHAT_ONLY,
            session_context={"document_context": {"total_documents": 10}}
        )

        assert result_chat["route"] == "direct_chat"
        assert result_chat["confidence"] == 1.0

        # Test RAG_ONLY mode
        result_rag = heuristic_route(
            user_input="hello",
            has_documents=True,
            session_mode=SessionMode.RAG_ONLY,
            session_context={"document_context": {"total_documents": 10}}
        )

        assert result_rag["route"] == "rag_needed"
        assert result_rag["confidence"] == 1.0

    async def test_routing_fallback_when_no_documents(self):
        """Test RAG_ONLY mode falls back to chat when no documents"""
        result = heuristic_route(
            user_input="what is in the document",
            has_documents=False,
            session_mode=SessionMode.RAG_ONLY,
            session_context={}
        )

        assert result["route"] == "direct_chat"
        assert result["confidence"] == 0.8
        assert "rag_only_fallback" in result["reasoning"]["rule"]


@pytest.mark.asyncio
class TestWorkflowResponseStructure:
    """Tests for workflow response structure validation"""

    def test_routing_result_structure(self):
        """Test that routing results have expected structure"""
        result = heuristic_route(
            user_input="test",
            has_documents=False,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        # Required fields
        assert "route" in result
        assert "confidence" in result
        assert "reasoning" in result

        # Route must be valid
        assert result["route"] in ["direct_chat", "rag_needed", "hybrid"]

        # Confidence must be in range
        assert 0.0 <= result["confidence"] <= 1.0

        # Reasoning must have required fields
        reasoning = result["reasoning"]
        assert "rule" in reasoning
        assert "description" in reasoning
        assert isinstance(reasoning["rule"], str)
        assert isinstance(reasoning["description"], str)

    def test_routing_metadata_includes_context_info(self):
        """Test that routing metadata includes context information"""
        session_context = {
            "document_context": {
                "total_documents": 5,
                "total_chunks": 25
            }
        }

        result = heuristic_route(
            user_input="what is in the document",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context=session_context
        )

        # Context info should be included in reasoning
        reasoning = result["reasoning"]
        assert "total_documents" in reasoning or "has_documents" in reasoning


@pytest.mark.asyncio
class TestMultilingualRoutingIntegration:
    """Tests for multilingual routing scenarios"""

    def test_turkish_keywords_integration(self):
        """Test Turkish keyword detection with session context"""
        turkish_queries = [
            "dokümanda ne yazıyor",
            "dosyayı özetle",
            "bul bana bu bilgiyi"
        ]

        session_context = {
            "document_context": {"total_documents": 3}
        }

        for query in turkish_queries:
            result = heuristic_route(
                user_input=query,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context=session_context
            )

            assert result["route"] == "rag_needed"
            assert result["confidence"] >= 0.8

    def test_mixed_language_routing(self):
        """Test routing with mixed language input"""
        result = heuristic_route(
            user_input="merhaba, can you summarize the document please",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={"document_context": {"total_documents": 2}}
        )

        # Greeting should take priority
        assert result["route"] == "direct_chat"
        assert result["reasoning"]["rule"] == "greeting_detection"


@pytest.mark.asyncio
class TestEdgeCasesIntegration:
    """Integration tests for edge cases"""

    def test_very_long_query_with_documents(self):
        """Test routing with very long queries"""
        long_query = " ".join(["word"] * 200)

        result = heuristic_route(
            user_input=long_query,
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={"document_context": {"total_documents": 5}}
        )

        # Should route to hybrid for ambiguous long query
        assert result["route"] == "hybrid"

    def test_empty_and_whitespace_queries(self):
        """Test routing with empty or whitespace-only queries"""
        test_inputs = ["", "   ", "\n\t  ", "    \n    "]

        for query in test_inputs:
            result = heuristic_route(
                user_input=query,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context={}
            )

            # Should default to chat
            assert result["route"] == "direct_chat"

    def test_special_characters_in_query(self):
        """Test routing with special characters"""
        queries_with_special_chars = [
            "what's in the document?",
            "document: summary!!!",
            "file@content.txt",
            "document #1, #2, #3"
        ]

        for query in queries_with_special_chars:
            result = heuristic_route(
                user_input=query,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context={"document_context": {"total_documents": 3}}
            )

            # Should detect document keywords despite special chars
            assert result["route"] in ["rag_needed", "hybrid"]


@pytest.mark.asyncio
class TestRoutingConsistency:
    """Tests for routing consistency and determinism"""

    def test_routing_is_deterministic(self):
        """Test that same input produces same routing decision"""
        session_context = {
            "document_context": {"total_documents": 5}
        }

        # Run routing 10 times with same input
        results = []
        for _ in range(10):
            result = heuristic_route(
                user_input="what does the document say",
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context=session_context
            )
            results.append(result)

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result["route"] == first_result["route"]
            assert result["confidence"] == first_result["confidence"]
            assert result["reasoning"]["rule"] == first_result["reasoning"]["rule"]

    def test_similar_queries_route_consistently(self):
        """Test that similar queries route to same path"""
        similar_queries = [
            "what is in the document",
            "what does the document say",
            "tell me what the document contains",
            "show me document content"
        ]

        results = []
        for query in similar_queries:
            result = heuristic_route(
                user_input=query,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context={"document_context": {"total_documents": 2}}
            )
            results.append(result["route"])

        # All should route to RAG
        assert all(route == "rag_needed" for route in results)


@pytest.mark.asyncio
class TestBackwardCompatibilityStructure:
    """Tests for backward compatibility of response structures"""

    def test_routing_result_backward_compatible(self):
        """Test that routing result structure is backward compatible"""
        result = heuristic_route(
            user_input="test query",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        # These fields must always exist for backward compatibility
        required_fields = ["route", "confidence", "reasoning"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Reasoning must have minimum structure
        assert "rule" in result["reasoning"]
        assert "description" in result["reasoning"]

    def test_session_mode_enum_values(self):
        """Test that SessionMode enum values are stable"""
        # These values should never change for backward compatibility
        assert SessionMode.AUTO.value == "auto"
        assert SessionMode.CHAT_ONLY.value == "chat_only"
        assert SessionMode.RAG_ONLY.value == "rag_only"

    def test_route_decision_values_stable(self):
        """Test that route decision values are stable"""
        valid_routes = ["direct_chat", "rag_needed", "hybrid"]

        # Test various scenarios
        test_cases = [
            ("hello", False, SessionMode.AUTO),
            ("what is in doc", True, SessionMode.AUTO),
            ("explain this", True, SessionMode.AUTO),
        ]

        for query, has_docs, mode in test_cases:
            result = heuristic_route(
                user_input=query,
                has_documents=has_docs,
                session_mode=mode,
                session_context={}
            )

            # Route must be one of the valid values
            assert result["route"] in valid_routes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

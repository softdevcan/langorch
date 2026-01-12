"""
Unit tests for router strategies

LangOrch v0.4.1 - Unified Workflow
Tests heuristic routing logic with various user inputs and contexts.
"""
import pytest

from app.workflows.nodes.router_strategies import heuristic_route
from app.core.enums import SessionMode


class TestHeuristicRoute:
    """Tests for heuristic_route function"""

    def test_explicit_chat_only_mode(self):
        """Test CHAT_ONLY mode override"""
        result = heuristic_route(
            user_input="what is in the document?",
            has_documents=True,
            session_mode=SessionMode.CHAT_ONLY,
            session_context={}
        )

        assert result["route"] == "direct_chat"
        assert result["confidence"] == 1.0
        assert "explicit_mode_override" in result["reasoning"]["rule"]

    def test_explicit_rag_only_mode(self):
        """Test RAG_ONLY mode override"""
        result = heuristic_route(
            user_input="hello there",
            has_documents=True,
            session_mode=SessionMode.RAG_ONLY,
            session_context={}
        )

        assert result["route"] == "rag_needed"
        assert result["confidence"] == 1.0
        assert "explicit_mode_override" in result["reasoning"]["rule"]

    def test_rag_only_mode_no_documents_fallback(self):
        """Test RAG_ONLY mode falls back to chat when no documents"""
        result = heuristic_route(
            user_input="what is in the document?",
            has_documents=False,
            session_mode=SessionMode.RAG_ONLY,
            session_context={}
        )

        assert result["route"] == "direct_chat"
        assert result["confidence"] == 0.8
        assert "rag_only_fallback" in result["reasoning"]["rule"]

    def test_greeting_detection_english(self):
        """Test greeting detection in English"""
        greetings = ["hello", "hi", "hey", "good morning", "greetings"]

        for greeting in greetings:
            result = heuristic_route(
                user_input=greeting,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context={}
            )

            assert result["route"] == "direct_chat"
            assert result["confidence"] == 0.95
            assert result["reasoning"]["rule"] == "greeting_detection"

    def test_greeting_detection_turkish(self):
        """Test greeting detection in Turkish"""
        greetings = ["merhaba", "selam", "günaydın", "nasılsın"]

        for greeting in greetings:
            result = heuristic_route(
                user_input=greeting,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context={}
            )

            assert result["route"] == "direct_chat"
            assert result["confidence"] == 0.95
            assert result["reasoning"]["rule"] == "greeting_detection"

    def test_small_talk_detection(self):
        """Test small talk detection"""
        small_talk = [
            "who are you",
            "what can you do",
            "thank you",
            "what's your name",
        ]

        for phrase in small_talk:
            result = heuristic_route(
                user_input=phrase,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context={}
            )

            assert result["route"] == "direct_chat"
            assert result["confidence"] == 0.9
            assert result["reasoning"]["rule"] == "small_talk_detection"

    def test_document_keywords_with_documents(self):
        """Test document-related queries with documents available"""
        queries = [
            "what does the document say",
            "summarize the paper",
            "find information about X in the files",
            "according to the document",
            "show me the content",
        ]

        session_context = {
            "document_context": {
                "total_documents": 2,
                "total_chunks": 10
            }
        }

        for query in queries:
            result = heuristic_route(
                user_input=query,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context=session_context
            )

            assert result["route"] == "rag_needed"
            assert result["confidence"] == 0.85
            assert result["reasoning"]["rule"] == "document_keywords_with_docs"

    def test_document_keywords_turkish(self):
        """Test Turkish document keywords"""
        queries = [
            "dokümanda ne yazıyor",
            "dosyayı özetle",
            "bul bana bu bilgiyi",
        ]

        session_context = {
            "document_context": {
                "total_documents": 1
            }
        }

        for query in queries:
            result = heuristic_route(
                user_input=query,
                has_documents=True,
                session_mode=SessionMode.AUTO,
                session_context=session_context
            )

            assert result["route"] == "rag_needed"
            assert result["confidence"] == 0.85

    def test_ambiguous_with_documents(self):
        """Test ambiguous query with documents (hybrid mode)"""
        result = heuristic_route(
            user_input="can you help me understand this concept better please",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={"document_context": {"total_documents": 3}}
        )

        assert result["route"] == "hybrid"
        assert result["confidence"] == 0.6
        assert result["reasoning"]["rule"] == "ambiguous_with_docs"

    def test_no_documents_available(self):
        """Test query when no documents available"""
        result = heuristic_route(
            user_input="tell me about machine learning",
            has_documents=False,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        assert result["route"] == "direct_chat"
        assert result["confidence"] == 0.8
        assert result["reasoning"]["rule"] == "default_chat"

    def test_short_query_default_chat(self):
        """Test very short query defaults to chat"""
        result = heuristic_route(
            user_input="explain",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        assert result["route"] == "direct_chat"
        assert result["confidence"] == 0.7
        assert result["reasoning"]["rule"] == "default_chat"

    def test_general_question_no_document_keywords(self):
        """Test general question without document keywords"""
        result = heuristic_route(
            user_input="how does photosynthesis work in plants",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={"document_context": {"total_documents": 2}}
        )

        # Should go to hybrid since query is substantial and has docs
        assert result["route"] == "hybrid"
        assert result["confidence"] == 0.6

    def test_context_metadata_included_in_response(self):
        """Test that context metadata is included in reasoning"""
        session_context = {
            "document_context": {
                "total_documents": 5,
                "total_chunks": 25
            }
        }

        result = heuristic_route(
            user_input="what does the document say about AI",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context=session_context
        )

        assert "total_documents" in result["reasoning"]
        assert result["reasoning"]["total_documents"] == 5

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive"""
        result = heuristic_route(
            user_input="WHAT DOES THE DOCUMENT SAY",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        assert result["route"] == "rag_needed"

    def test_partial_keyword_matching(self):
        """Test that partial keyword matching works"""
        result = heuristic_route(
            user_input="the documentation shows that",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        # "document" is in "documentation"
        assert result["route"] == "rag_needed"

    def test_multiple_keywords_increase_confidence(self):
        """Test query with multiple document keywords"""
        result = heuristic_route(
            user_input="what does the document say about the file content in the paper",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        assert result["route"] == "rag_needed"
        assert len(result["reasoning"].get("matched_keywords", [])) >= 3


class TestRoutingStrategyEdgeCases:
    """Tests for edge cases and error handling"""

    def test_empty_input(self):
        """Test with empty user input"""
        result = heuristic_route(
            user_input="",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        # Should default to chat for empty input
        assert result["route"] == "direct_chat"

    def test_whitespace_only_input(self):
        """Test with whitespace-only input"""
        result = heuristic_route(
            user_input="   \n\t  ",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        assert result["route"] == "direct_chat"

    def test_very_long_query(self):
        """Test with very long query"""
        long_query = " ".join(["word"] * 100)
        result = heuristic_route(
            user_input=long_query,
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        # Long query should trigger hybrid if has docs
        assert result["route"] == "hybrid"

    def test_mixed_language_query(self):
        """Test query with mixed English and Turkish"""
        result = heuristic_route(
            user_input="merhaba, can you summarize the document",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        # Should catch both greeting (Turkish) and document keyword (English)
        # Greeting has higher priority
        assert result["route"] == "direct_chat"
        assert result["reasoning"]["rule"] == "greeting_detection"


class TestRoutingReasoningMetadata:
    """Tests for routing reasoning metadata"""

    def test_reasoning_contains_rule(self):
        """Test that reasoning always contains rule"""
        result = heuristic_route(
            user_input="hello",
            has_documents=False,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        assert "rule" in result["reasoning"]
        assert isinstance(result["reasoning"]["rule"], str)

    def test_reasoning_contains_description(self):
        """Test that reasoning contains description"""
        result = heuristic_route(
            user_input="what is in the document",
            has_documents=True,
            session_mode=SessionMode.AUTO,
            session_context={}
        )

        assert "description" in result["reasoning"]
        assert isinstance(result["reasoning"]["description"], str)

    def test_confidence_in_valid_range(self):
        """Test that confidence is always between 0 and 1"""
        test_cases = [
            ("hello", False, SessionMode.AUTO),
            ("what is in the document", True, SessionMode.AUTO),
            ("explain this", True, SessionMode.CHAT_ONLY),
        ]

        for user_input, has_docs, mode in test_cases:
            result = heuristic_route(
                user_input=user_input,
                has_documents=has_docs,
                session_mode=mode,
                session_context={}
            )

            assert 0.0 <= result["confidence"] <= 1.0

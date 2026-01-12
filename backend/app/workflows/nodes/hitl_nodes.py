"""
Human-in-the-Loop (HITL) nodes for LangGraph workflows

This module provides node creators for workflow interruption points where
human approval or input is required before continuing execution.
"""
from typing import Dict, Any, Callable
from uuid import UUID
from langgraph.types import interrupt, Command
import structlog

from app.workflows.state import WorkflowState
from app.services.litellm_service import LiteLLMService

logger = structlog.get_logger()


def create_hitl_node(config: Dict[str, Any]) -> Callable:
    """
    Create Human-in-the-Loop approval node

    This node interrupts workflow execution and waits for human approval
    before continuing. Used for critical decision points.

    Config:
        prompt: Question/prompt to display to user
        approval_required: Whether approval is mandatory (default: True)
        timeout_seconds: Optional timeout for approval (not implemented yet)

    Returns:
        Callable node function (state -> state)
    """
    prompt = config.get("prompt", "Do you approve this action?")
    approval_required = config.get("approval_required", True)

    async def hitl_node(state: WorkflowState) -> WorkflowState:
        """
        HITL approval point

        Interrupts workflow and requests human approval.
        Workflow will pause here until user responds via API.
        """
        tenant_id = state["metadata"].get("tenant_id")

        # Prepare approval request data
        approval_data = {
            "type": "approval_request",
            "prompt": prompt,
            "approval_required": approval_required,
            "state_summary": {
                "messages_count": len(state.get("messages", [])),
                "documents_count": len(state.get("documents", [])),
                "context_length": len(state.get("context", "")),
                "has_generation": bool(state.get("generation"))
            },
            "metadata": {
                "tenant_id": tenant_id,
                "session_id": state["metadata"].get("session_id")
            }
        }

        logger.info(
            "hitl_interrupt",
            tenant_id=tenant_id,
            prompt=prompt,
            approval_required=approval_required
        )

        # Interrupt workflow and wait for user response
        # This will cause the workflow to pause here
        # User must call resume API with their response
        user_response = interrupt(approval_data)

        # Process user response (this executes after resume)
        approved = user_response.get("approved", False)
        feedback = user_response.get("feedback", "")

        logger.info(
            "hitl_approval_received",
            tenant_id=tenant_id,
            approved=approved,
            has_feedback=bool(feedback)
        )

        # Update state with approval result
        return {
            **state,
            "approved": approved,
            "user_feedback": feedback,
            "intermediate_results": {
                **state.get("intermediate_results", {}),
                "hitl_approved": approved,
                "hitl_feedback": feedback
            }
        }

    return hitl_node


def create_hallucination_check_node(config: Dict[str, Any]) -> Callable:
    """
    Create hallucination detection node with HITL

    This node checks if generated content is grounded in retrieved documents.
    If hallucination is detected (low score), it interrupts for human review.

    Config:
        threshold: Minimum grounding score 0-1 (default: 0.7)
        model: Model to use for grading (default: "gpt-4")
        provider: Provider hint (optional)
        auto_regenerate: Whether to auto-regenerate on low score (default: False)

    Returns:
        Callable node function (state -> state)
    """
    threshold = config.get("threshold", 0.7)
    model = config.get("model", "gpt-4")
    provider = config.get("provider")
    auto_regenerate = config.get("auto_regenerate", False)

    async def hallucination_check(state: WorkflowState) -> WorkflowState:
        """
        Check for hallucinations and request human review if needed

        Grades the generated answer against the source documents.
        Low scores trigger HITL intervention.
        """
        tenant_id_str = state["metadata"].get("tenant_id")
        tenant_id = UUID(tenant_id_str) if tenant_id_str else None

        if not tenant_id:
            logger.error("hallucination_check_missing_tenant_id")
            return {
                **state,
                "error": "Missing tenant_id in metadata"
            }

        # Get generation and documents
        generation = state.get("generation", "")
        documents = state.get("documents", [])

        if not generation:
            logger.warning(
                "hallucination_check_no_generation",
                tenant_id=str(tenant_id)
            )
            return state  # No generation to check

        if not documents:
            logger.warning(
                "hallucination_check_no_documents",
                tenant_id=str(tenant_id)
            )
            # No documents means high hallucination risk
            state["hallucination_score"] = 0.0
        else:
            try:
                # Initialize LLM service
                llm_service = LiteLLMService(tenant_id=tenant_id, provider=provider)

                # Prepare documents text
                docs_text = "\n\n".join([
                    f"Document {i+1}:\n{doc['payload']['content']}"
                    for i, doc in enumerate(documents)
                ])

                # Create grading prompt
                prompt = f"""Check if the answer is grounded in the provided documents.

Documents:
{docs_text}

Answer:
{generation}

Rate from 0.0 to 1.0 how well the answer is supported by the documents.
- 1.0 = All information comes directly from the documents
- 0.5 = Some information is inferred or partially from documents
- 0.0 = Answer contains information not in documents (hallucination)

Respond with just a number between 0.0 and 1.0."""

                messages = [{"role": "user", "content": prompt}]

                response = await llm_service.complete(
                    messages=messages,
                    model=model,
                    temperature=0  # Deterministic grading
                )

                # Parse score
                try:
                    score_text = response["content"].strip()
                    score = float(score_text)
                    score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                except (ValueError, TypeError):
                    logger.warning(
                        "hallucination_score_parse_error",
                        tenant_id=str(tenant_id),
                        response_content=response["content"]
                    )
                    score = 0.5  # Default to uncertain

                state["hallucination_score"] = score

                logger.info(
                    "hallucination_check_completed",
                    tenant_id=str(tenant_id),
                    score=score,
                    threshold=threshold,
                    model=model
                )

            except Exception as e:
                logger.error(
                    "hallucination_check_error",
                    tenant_id=str(tenant_id),
                    error=str(e)
                )
                state["hallucination_score"] = 0.5  # Default to uncertain

        # Check if score is below threshold
        score = state.get("hallucination_score", 0.5)

        if score < threshold:
            # Low score - potential hallucination detected
            logger.warning(
                "potential_hallucination_detected",
                tenant_id=str(tenant_id),
                score=score,
                threshold=threshold
            )

            # Interrupt for human review
            user_action = interrupt({
                "type": "hallucination_detected",
                "score": score,
                "threshold": threshold,
                "generation": generation,
                "documents_count": len(documents),
                "message": f"The generated answer may contain hallucinations (score: {score:.2f}). What would you like to do?",
                "options": {
                    "regenerate": "Regenerate the answer",
                    "edit": "Edit the answer manually",
                    "accept": "Accept the answer as-is"
                }
            })

            # Process user action
            action = user_action.get("action", "regenerate")

            logger.info(
                "hallucination_user_action",
                tenant_id=str(tenant_id),
                action=action
            )

            if action == "regenerate":
                # Return command to go back to generator node
                return Command(goto="generator")

            elif action == "edit":
                # User provided edited text
                edited_text = user_action.get("edited_text", generation)
                state["generation"] = edited_text

                # Update last message if it exists
                if state.get("messages") and len(state["messages"]) > 0:
                    from langchain_core.messages import AIMessage
                    # Replace last AI message with edited version
                    state["messages"] = state["messages"][:-1] + [
                        AIMessage(content=edited_text)
                    ]

            elif action == "accept":
                # User accepts despite low score
                pass

            # Update intermediate results
            state["intermediate_results"] = {
                **state.get("intermediate_results", {}),
                "hallucination_action": action,
                "hallucination_score": score
            }

        return state

    return hallucination_check

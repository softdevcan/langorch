"""
Workflow builder for creating LangGraph workflows from JSON configurations

This module provides the WorkflowBuilder class that constructs StateGraph instances
from JSON configuration, supporting dynamic node registration, conditional edges,
and checkpoint-based state persistence.
"""
from typing import Dict, Any, List, Callable, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import structlog

from app.workflows.state import WorkflowState

logger = structlog.get_logger()


class WorkflowBuilder:
    """
    Build LangGraph workflows from JSON configuration

    Supports:
    - Dynamic node registration
    - Conditional edges
    - Checkpoint-based state persistence
    - JSON schema-based workflow definition
    """

    def __init__(self, checkpointer: Optional[AsyncPostgresSaver] = None):
        """
        Initialize workflow builder

        Args:
            checkpointer: PostgreSQL checkpointer for state persistence
        """
        self.checkpointer = checkpointer
        self.node_registry: Dict[str, Callable] = {}
        self.condition_registry: Dict[str, Callable] = {}

    def register_node(self, node_id: str, node_func: Callable):
        """
        Register a node function

        Args:
            node_id: Unique node identifier
            node_func: Callable node function (state -> state)
        """
        self.node_registry[node_id] = node_func
        logger.debug("node_registered", node_id=node_id)

    def register_condition(self, condition_id: str, condition_func: Callable):
        """
        Register a conditional routing function

        Args:
            condition_id: Unique condition identifier
            condition_func: Callable condition function (state -> str)
        """
        self.condition_registry[condition_id] = condition_func
        logger.debug("condition_registered", condition_id=condition_id)

    def build_from_config(self, config: Dict[str, Any]) -> StateGraph:
        """
        Build workflow from JSON configuration

        Config structure:
        {
            "name": "workflow_name",
            "version": "1.0",
            "description": "Workflow description",
            "state_schema": {...},  # Optional: custom state schema
            "nodes": [
                {
                    "id": "node1",
                    "type": "llm|retriever|tool|human_in_loop",
                    "config": {...}
                },
                ...
            ],
            "edges": [
                {
                    "source": "node1" | "__start__",
                    "target": "node2" | "__end__",
                    "condition": "optional_condition_id",
                    "mapping": {"route1": "node3", "route2": "node4"}  # For conditional edges
                },
                ...
            ]
        }

        Args:
            config: Workflow configuration dictionary

        Returns:
            StateGraph: Compiled StateGraph ready for execution
        """
        workflow_name = config.get("name", "unnamed_workflow")

        # Create graph with WorkflowState
        graph = StateGraph(WorkflowState)

        # Add nodes
        nodes_count = 0
        for node_config in config.get("nodes", []):
            node_id = node_config["id"]
            node_type = node_config["type"]
            node_params = node_config.get("config", {})

            # Get node function
            node_func = self._get_node_function(node_type, node_params)

            # Add to graph
            graph.add_node(node_id, node_func)
            nodes_count += 1

            logger.debug(
                "node_added",
                workflow=workflow_name,
                node_id=node_id,
                node_type=node_type
            )

        # Add edges
        edges_count = 0
        for edge in config.get("edges", []):
            source = edge["source"]
            target = edge["target"]

            # Handle START and END special nodes
            if source == "__start__":
                graph.add_edge(START, target)
            elif target == "__end__":
                graph.add_edge(source, END)
            else:
                # Check for conditional edges
                condition = edge.get("condition")
                if condition:
                    # Conditional edge
                    condition_func = self._get_condition_function(condition)
                    mapping = edge.get("mapping", {})

                    graph.add_conditional_edges(
                        source,
                        condition_func,
                        mapping
                    )

                    logger.debug(
                        "conditional_edge_added",
                        workflow=workflow_name,
                        source=source,
                        condition=condition,
                        mapping=mapping
                    )
                else:
                    # Simple edge
                    graph.add_edge(source, target)

            edges_count += 1

        logger.info(
            "workflow_built",
            workflow_name=workflow_name,
            version=config.get("version", "unknown"),
            nodes_count=nodes_count,
            edges_count=edges_count
        )

        return graph

    def _get_node_function(self, node_type: str, config: Dict[str, Any]) -> Callable:
        """
        Get or create node function based on type

        Args:
            node_type: Type of node (llm, retriever, tool, human_in_loop)
            config: Node configuration

        Returns:
            Callable: Node function

        Raises:
            ValueError: If node type is unknown
        """
        # Check if node type is registered
        if node_type in self.node_registry:
            return self.node_registry[node_type]

        # Dynamic node creation based on type
        if node_type == "llm":
            from app.workflows.nodes.llm_nodes import create_llm_node
            return create_llm_node(config)

        elif node_type == "rag_generator":
            from app.workflows.nodes.llm_nodes import create_rag_generator_node
            return create_rag_generator_node(config)

        elif node_type == "retriever":
            from app.workflows.nodes.retriever_nodes import create_retriever_node
            return create_retriever_node(config)

        elif node_type == "relevance_grader":
            from app.workflows.nodes.retriever_nodes import create_relevance_grader_node
            return create_relevance_grader_node(config)

        elif node_type == "human_in_loop":
            from app.workflows.nodes.hitl_nodes import create_hitl_node
            return create_hitl_node(config)

        elif node_type == "hallucination_checker":
            from app.workflows.nodes.hitl_nodes import create_hallucination_check_node
            return create_hallucination_check_node(config)

        else:
            raise ValueError(f"Unknown node type: {node_type}")

    def _get_condition_function(self, condition_id: str) -> Callable:
        """
        Get conditional routing function

        Args:
            condition_id: Condition identifier

        Returns:
            Callable: Condition function (state -> str)

        Raises:
            ValueError: If condition is not registered
        """
        if condition_id in self.condition_registry:
            return self.condition_registry[condition_id]

        # Default conditions
        if condition_id == "has_relevant_docs":
            return lambda state: "continue" if len(state.get("documents", [])) > 0 else "no_docs"

        elif condition_id == "needs_review":
            return lambda state: "review" if state.get("hallucination_score", 1.0) < 0.7 else "approved"

        elif condition_id == "approved":
            return lambda state: "approved" if state.get("approved", False) else "rejected"

        else:
            raise ValueError(f"Unknown condition: {condition_id}")

    async def compile(self, graph: StateGraph):
        """
        Compile graph with checkpointer

        Args:
            graph: StateGraph to compile

        Returns:
            Compiled graph ready for execution
        """
        if self.checkpointer:
            compiled = graph.compile(checkpointer=self.checkpointer)
            logger.debug("workflow_compiled_with_checkpointer")
        else:
            compiled = graph.compile()
            logger.debug("workflow_compiled_without_checkpointer")

        return compiled

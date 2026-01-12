/**
 * Pre-built workflow templates
 *
 * These templates match the backend workflow templates
 * and can be used for quick execution.
 */
import type { WorkflowConfig } from './types';

export const RAG_WORKFLOW_TEMPLATE: WorkflowConfig = {
  name: "rag_workflow",
  version: "1.0",
  description: "Retrieval-Augmented Generation workflow",
  nodes: [
    {
      id: "retriever",
      type: "retriever",
      config: {
        top_k: 5,
        score_threshold: 0.7
      }
    },
    {
      id: "grader",
      type: "relevance_grader",
      config: {
        model: "ollama/llama3.2"
      }
    },
    {
      id: "generator",
      type: "rag_generator",
      config: {
        model: "ollama/llama3.2",
        temperature: 0.7,
        include_sources: true
      }
    }
  ],
  edges: [
    { source: "__start__", target: "retriever" },
    { source: "retriever", target: "grader" },
    { source: "grader", target: "generator" },
    { source: "generator", target: "__end__" }
  ]
};

export const SIMPLE_CHAT_WORKFLOW: WorkflowConfig = {
  name: "simple_chat",
  version: "1.0",
  description: "Simple conversational chat",
  nodes: [
    {
      id: "chat",
      type: "llm",
      config: {
        model: "ollama/llama3.2",
        system_prompt: "You are a helpful AI assistant.",
        temperature: 0.7
      }
    }
  ],
  edges: [
    { source: "__start__", target: "chat" },
    { source: "chat", target: "__end__" }
  ]
};

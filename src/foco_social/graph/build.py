"""Arma el grafo de LangGraph.

    START -> plan_queries -> retrieve -> split_topic --(cola con pendientes)--> split_topic
                                                   \\--(cola vacía)----------> END

split_topic se repite hasta vaciar la cola: cada tópico generado por debajo de la
profundidad pedida se vuelve a encolar para buscar subtópicos.
"""

from langgraph.graph import END, START, StateGraph

from foco_social.config import Settings
from foco_social.graph.nodes import Nodes
from foco_social.graph.state import AgentState
from foco_social.llm import LLM
from foco_social.sources import TweetSource


def _route(state: AgentState) -> str:
    return "split_topic" if state.get("queue") else END


def build_graph(source: TweetSource, llm: LLM, settings: Settings):
    nodes = Nodes(source, llm, settings)
    graph = StateGraph(AgentState)
    graph.add_node("plan_queries", nodes.plan_queries)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("split_topic", nodes.split_topic)

    graph.add_edge(START, "plan_queries")
    graph.add_edge("plan_queries", "retrieve")
    graph.add_conditional_edges("retrieve", _route, ["split_topic", END])
    graph.add_conditional_edges("split_topic", _route, ["split_topic", END])
    return graph.compile()

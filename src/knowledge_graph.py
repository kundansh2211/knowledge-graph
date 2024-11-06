import os
import json
import openai
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from neo4j import GraphDatabase
import PyPDF2
from dotenv import load_dotenv
from langchain_core.runnables.graph import Node
from langchain_community.graphs.graph_document import Relationship



load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

CACHE_FILE_PATH = "data/graph_cache.json"

llm = ChatOpenAI(temperature=0, model_name="gpt-4-turbo")
llm_transformer = LLMGraphTransformer(llm=llm)



def create_neo4j_session():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    return driver

def read_pdf_file(file_path):
    pdf_file = open(file_path, "rb")
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in range(len(pdf_reader.pages)):
        text += pdf_reader.pages[page].extract_text()
    pdf_file.close()
    return text

def load_cached_graph():
    """Load graph data from JSON cache."""
    if os.path.exists(CACHE_FILE_PATH):
        with open(CACHE_FILE_PATH, "r") as f:
            return json.load(f)
    return None

def save_graph_to_cache(nodes, relationships):
    """Save nodes and relationships to JSON cache."""
    graph_data = {
        "nodes": [{"id": node.id, "type": node.type, "properties": node.properties} for node in nodes],
        "relationships": [{
            "source_id": rel.source.id,
            "target_id": rel.target.id,
            "type": rel.type,
            "properties": rel.properties
        } for rel in relationships]
    }
    with open(CACHE_FILE_PATH, "w") as f:
        json.dump(graph_data, f)

def extract_graph_from_text(text):
    """Extract graph from text with caching."""
    cached_graph = load_cached_graph()
    if cached_graph:
        # Load nodes and relationships from cache
        nodes = [Node(**node_data) for node_data in cached_graph["nodes"]]
        relationships = [Relationship(
            source=Node(id=rel["source_id"], type="", properties={}),
            target=Node(id=rel["target_id"], type="", properties={}),
            type=rel["type"],
            properties=rel.get("properties", {})
        ) for rel in cached_graph["relationships"]]
        print("Loaded graph from cache.")
    else:
        # Extract graph from text using LLMGraphTransformer
        documents = [Document(page_content=text)]
        graph_documents = llm_transformer.convert_to_graph_documents(documents)
        nodes = graph_documents[0].nodes
        relationships = graph_documents[0].relationships
        
        # Save to cache
        save_graph_to_cache(nodes, relationships)
        print("Graph saved to cache.")

    return nodes, relationships

def construct_knowledge_graph(driver, nodes, relationships):
    """Write nodes and relationships to Neo4j."""
    with driver.session() as session:
        for node in nodes:
            session.run(
                """
                MERGE (n:Entity {id: $id, name: $name, type: $type})
                """,
                id=node.id,
                name=node.id,
                type=node.type
            )

        for relationship in relationships:
            session.run(
                """
                MATCH (a:Entity {id: $from_id}), (b:Entity {id: $to_id})
                MERGE (a)-[:RELATIONSHIP {type: $type}]->(b)
                """,
                from_id=relationship.source.id,
                to_id=relationship.target.id,
                type=relationship.type
            )

if __name__ == "__main__":
    input_data_dir = 'data'
    pdf_file_name = 'Homogeneous_length_function.pdf'
    file_path = f'{input_data_dir}/{pdf_file_name}'
    
    pdf_text = read_pdf_file(file_path)

    nodes, relationships = extract_graph_from_text(pdf_text)
    
    print("Nodes:", nodes)
    print("Relationships:", relationships)
    
    with create_neo4j_session() as driver:
        construct_knowledge_graph(driver, nodes, relationships)

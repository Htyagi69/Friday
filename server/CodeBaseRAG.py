from google import  genai
from dotenv import load_dotenv
import os
import chromadb
from pathlib import Path
import re
import tree_sitter_python as tspython
from tree_sitter import Language,Parser,Query,QueryCursor
import tree_sitter_typescript
import uuid

load_dotenv()

PY_LANGUAGE=Language(tspython.language())
parser=Parser(PY_LANGUAGE)

TSX_LANGUAGE = Language(tree_sitter_typescript.language_tsx())
parser_tsx = Parser(TSX_LANGUAGE)

IGNORE_DIRS = {
    # Version control & Environment
    ".git",
    ".env",
    ".venv",
    "__pycache__",
    
    # Dependencies
    "node_modules",
    ".pnpm-store",
    ".yarn",
    "vendor",

    # Build & Distribution outputs
    "dist",
    "build",
    "out",
    ".next",
    ".nuxt",
    ".output",
    ".svelte-kit",
    "storybook-static",

    # Caches & Tooling metadata
    ".cache",
    ".turbo",
    ".parcel-cache",
    ".swc",
    ".tsbuildinfo",
    ".eslintcache",
    ".vite",

    # Testing & Coverage reports
    "coverage",
    ".nyc_output",
    "cypress",
    "playwright-report",
    "blob-report"
}

IGNORE_EXTENSIONS={
      ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".mp4",
    ".mp3",
    ".zip",
    ".exe",
    ".svg",
    "-lock.json",
     ".lock",
}

IGNORE_FILENAMES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock"
}


chroma_client=chromadb.PersistentClient(path="../Friday_embed")

def get_project_collection(project_name:str):
    folder_name=Path(project_path).resolve().name

    valid_name=re.sub(r"[^a-zA-Z0-9_-]","_",folder_name).lower()

    if len(valid_name)<3:
        valid_name=f"proj_{valid_name}"
    return chroma_client.get_or_create_collection(name=valid_name[:63])
    
# collection=chroma_client.get_or_create_collection(name="Friday_Memo")

def get_parent_component_name(node) -> str:
    """Walks up the AST to find the enclosing component or function name."""
    current = node.parent
    while current:
        if current.type == 'variable_declarator':
            id_node = current.child_by_field_name('name')
            if id_node:
                return id_node.text.decode('utf8')
        elif current.type in ['class_definition', 'function_declaration']:
            name_node = current.child_by_field_name('name')
            if name_node:
                return name_node.text.decode('utf8')
        current = current.parent
    return "Global/Top-Level"

def extract_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")

def scan_folder(project_path:str):
    root=Path(project_path)
    
    files=[]
    
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue

        if path.name in IGNORE_FILENAMES or path.suffix.lower() in IGNORE_EXTENSIONS:
            continue
        text=extract_text(path)
        files.append({
            "path":str(path.relative_to(root)),
            "extension":path.suffix.lower(),
            "size":path.stat().st_size,
            "text":text
        })
        index_source_file(project_path,str(path),text)
    return files

def optimal_code_chunker(file_path: str, source_code: str) -> list[dict]:
    bytes_code = bytes(source_code, "utf8")
    chunks = []
    try:
        tree = parser_tsx.parse(bytes_code)
        query_string = """
            (class_definition) @class_node
            (function_definition) @function_node
            """

        query_string_tsx = """
        (lexical_declaration (variable_declarator value: (arrow_function))) @block
        (function_declaration) @block
        (expression_statement) @block
        (jsx_element) @block
        """
        query = Query(TSX_LANGUAGE, query_string_tsx)
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        seen_ranges = set()

        for capture_name, nodes in captures.items():
            for node in nodes:
                if (node.end_point[0] - node.start_point[0]) < 1:
                    continue
                range_key = (node.start_byte, node.end_byte)
                if range_key in seen_ranges:
                    continue
                seen_ranges.add(range_key)

                parent_name = get_parent_component_name(node)
                raw_node_text = bytes_code[node.start_byte:node.end_byte].decode("utf8")
                
                augmented_text = (
                    f"File Path: {file_path}\n"
                    f"Scope Context: {parent_name}\n"
                    f"Structure Type: {node.type}\n"
                    f"---\n"
                    f"{raw_node_text}"
                )

                chunks.append({
                    "text": augmented_text,
                    "metadata": {
                        "source": file_path,
                        "parent_struture": parent_name,
                        "start_line": int(node.start_point[0] + 1),
                        "end_line": int(node.end_point[0] + 1),
                        "type": str(node.type)
                    }
                })
    except Exception as e:
        print(f"AST Parsing skipped for {file_path}: {e}")

    if not chunks and source_code.strip():
        augmented_text = (
            f"File Path: {file_path}\n"
            f"Scope Context: Raw File Context\n"
            f"Structure Type: full_file\n"
            f"---\n"
            f"{source_code}"
        )
        chunks.append({
            "text": augmented_text,
            "metadata": {
                "file_path": file_path,
                "parent_struture": "Global",
                "start_line": 1,
                "end_line": len(source_code.splitlines()),
                "type": "raw_file"
            }
        })

    return chunks

parent_document_store = {}

def index_source_file(project_path:str,file_path: str, source_code: str):
    collection=get_project_collection(project_path)

    existing=collection.get(
        where={"source":file_path}
        )
    if existing and existing["ids"]:
      print(f"Skipping chunking of {file_path} as it already exists")
      return
    
    parent_id = str(uuid.uuid4())
    parent_document_store[parent_id] = source_code
    child_chunks = optimal_code_chunker(file_path, source_code)
    
    ids, documents, metadatas = [], [], []
    
    for chunk in child_chunks:
        ids.append(str(uuid.uuid4()))
        documents.append(chunk["text"])
        
        meta = chunk["metadata"]
        meta["parent_id"] = parent_id
        metadatas.append(meta)
    if documents:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f" Successfully indexed {len(documents)} granular chunks for {file_path}")

sample_react_file = """
     import React, { useState } from 'react';
     
     export const AuthDashboard = () => {
         const [token, setToken] = useState(null);
     
         const executeLogin = async (credentials) => {
             const response = await api.post('/auth/login', credentials);
             setToken(response.data.jwt);
             localStorage.setItem('session_token', response.data.jwt);
         };
     
         return (
             <div className="dashboard-container">
                 <h3>Security Center</h3>
                 <button onClick={executeLogin}>Login</button>
             </div>
         );
     };
"""

example_python_code = """
     class DataProcessor:
         def __init__(self, data):
             self.data = data
     
         def clean_text(self):
             return self.data.strip().lower()
     
     def calculate_metrics(x, y):
         return x + y
"""

# index_source_file("src/components/AuthDashboard.tsx", sample_react_file)

# print("-"*60)
# extracted_chunks=optimal_code_chunker("src/components/AuthDashboard.tsx",sample_react_file)

# for i, chunk in enumerate(extracted_chunks):
#     print(f"--- Chunk {i+1} ({chunk['metadata']['type']}) ---")
#     print(chunk['text'])

project_path=input(f">>").strip()

scan_folder(project_path)

client=genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

user_input=input(f">>")

max_fetch=35

collection=get_project_collection(project_path)
result=collection.query(
    query_texts=[user_input],
    n_results=max_fetch
)

retrieved_docs = result.get("documents", [[]])[0]
retrieved_distances = result.get("distances", [[]])[0]

filtered_chunks=[
    doc for doc,dist in zip(retrieved_docs,retrieved_distances)
    if dist<0.8
]
if not filtered_chunks and retrieved_docs:
    filtered_chunks = retrieved_docs[:2]
context_str = "\n\n---\n\n".join(filtered_chunks)

prompt=f"""
  you are an helful assistant.
  Answer the following question with the given context below.

  if answer is not prsent in context,say:
  "I dont Know the answer based on given context"
  Question:
  {user_input}\n\n

 Context:
 \n{context_str}

"""

while True:
   response=client.models.generate_content_stream( 
       model="gemini-2.5-flash",
       contents=prompt,
          config={
           "system_instruction": "Analyze the structure, tech stack, and quality using strictly the provided source files."
       }
   )
   
   for res in response:
       print(res.text,end="")


"""
CHILL Language Server Protocol (LSP) Server
Based on ITU-T Recommendation Z.200 (1999)

Implements LSP for CHILL, enabling IDE features:
- Code completion
- Hover information
- Go to definition
- Find references
- Document symbols
"""

import json
import sys
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from chill_semantic_parser import (
    ChillParser, ChillSemanticModel, ChillMode,
    CHILL_RESERVED_WORDS, CHILL_PREDEFINED,
    get_completions_at_position, get_hover_info
)


@dataclass
class LSPPosition:
    """LSP position (line, character)"""
    line: int
    character: int

    @classmethod
    def from_dict(cls, data: Dict) -> 'LSPPosition':
        return cls(line=data['line'], character=data['character'])

    def to_dict(self) -> Dict:
        return {'line': self.line, 'character': self.character}


@dataclass
class LSPRange:
    """LSP range (start, end positions)"""
    start: LSPPosition
    end: LSPPosition

    @classmethod
    def from_dict(cls, data: Dict) -> 'LSPRange':
        return cls(
            start=LSPPosition.from_dict(data['start']),
            end=LSPPosition.from_dict(data['end'])
        )

    def to_dict(self) -> Dict:
        return {
            'start': self.start.to_dict(),
            'end': self.end.to_dict()
        }


@dataclass
class LSPLocation:
    """LSP location (URI + range)"""
    uri: str
    range: LSPRange

    def to_dict(self) -> Dict:
        return {
            'uri': self.uri,
            'range': self.range.to_dict()
        }


# Keyword documentation for hover
KEYWORD_DOCS = {
    'MODULE': 'Defines a module - the basic unit of CHILL program structure',
    'DCL': 'Declares a variable with a specified mode (type)',
    'NEWMODE': 'Defines a new mode (type) derived from existing modes',
    'SYNMODE': 'Defines a synonym mode (type alias)',
    'SYN': 'Defines a synonym (named constant)',
    'PROC': 'Defines a procedure',
    'PROCESS': 'Defines a concurrent process',
    'SIGNAL': 'Defines a signal for inter-process communication',
    'BUFFER': 'Declares a buffer for inter-process message passing',
    'EVENT': 'Declares an event for process synchronization',
    'REGION': 'Defines a protected region for mutual exclusion',
    'IF': 'Conditional statement',
    'THEN': 'Introduces the consequent of IF',
    'ELSE': 'Introduces the alternative of IF',
    'ELSIF': 'Introduces an alternative condition',
    'FI': 'Terminates IF statement',
    'CASE': 'Case selection statement',
    'ESAC': 'Terminates CASE statement',
    'DO': 'Begins a loop construct',
    'OD': 'Terminates a DO loop',
    'WHILE': 'Loop while condition is true',
    'FOR': 'Counted loop',
    'EXIT': 'Exit from a loop',
    'RETURN': 'Return from procedure with optional value',
    'GOTO': 'Unconditional jump (discouraged)',
    'SEND': 'Send a signal to a process',
    'RECEIVE': 'Receive a signal from a process',
    'DELAY': 'Delay process execution for a duration',
    'START': 'Start a new process instance',
    'STOP': 'Stop the current process',
    'BEGIN': 'Begin a block',
    'END': 'End a block or construct',
    'GRANT': 'Make names visible outside module',
    'SEIZE': 'Access names from another module',
    'INT': 'Integer mode',
    'BOOL': 'Boolean mode (TRUE/FALSE)',
    'CHAR': 'Character mode',
    'CHARS': 'Character string mode',
    'BOOLS': 'Bit string mode',
    'SET': 'Enumeration mode',
    'RANGE': 'Integer subrange mode',
    'POWERSET': 'Set of discrete values mode',
    'REF': 'Reference (pointer) mode',
    'STRUCT': 'Structure mode (record)',
    'ARRAY': 'Array mode',
    'STATIC': 'Static storage duration',
    'INIT': 'Initialize with value',
    'LOC': 'Local (stack) storage',
    'READ': 'Read-only attribute',
    'AND': 'Logical AND operator',
    'OR': 'Logical OR operator',
    'NOT': 'Logical NOT operator',
    'XOR': 'Logical exclusive OR operator',
    'ANDIF': 'Short-circuit AND (evaluates right only if left is TRUE)',
    'ORIF': 'Short-circuit OR (evaluates right only if left is FALSE)',
    'MOD': 'Modulo operator',
    'REM': 'Remainder operator',
    'TRUE': 'Boolean true value',
    'FALSE': 'Boolean false value',
    'NULL': 'Null reference value',
}


class ChillLSPServer:
    """
    LSP Server for CHILL
    Handles LSP requests and responses
    """

    def __init__(self):
        self.documents: Dict[str, str] = {}  # URI -> document content
        self.models: Dict[str, ChillSemanticModel] = {}  # URI -> semantic model

    def handle_request(self, request: Dict) -> Optional[Dict]:
        """Handle an LSP request"""
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')

        if method == 'initialize':
            return self._handle_initialize(request_id)
        elif method == 'initialized':
            return None  # Notification
        elif method == 'textDocument/didOpen':
            self._handle_did_open(params)
            return None
        elif method == 'textDocument/didChange':
            self._handle_did_change(params)
            return None
        elif method == 'textDocument/didClose':
            self._handle_did_close(params)
            return None
        elif method == 'textDocument/completion':
            return self._handle_completion(request_id, params)
        elif method == 'textDocument/hover':
            return self._handle_hover(request_id, params)
        elif method == 'textDocument/definition':
            return self._handle_definition(request_id, params)
        elif method == 'textDocument/references':
            return self._handle_references(request_id, params)
        elif method == 'textDocument/documentSymbol':
            return self._handle_document_symbol(request_id, params)
        elif method == 'shutdown':
            return {'jsonrpc': '2.0', 'id': request_id, 'result': None}
        else:
            if request_id:
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {
                        'code': -32601,
                        'message': f'Method not found: {method}'
                    }
                }
            return None

    def _handle_initialize(self, request_id: Optional[int]) -> Dict:
        """Handle initialize request"""
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'capabilities': {
                    'textDocumentSync': {
                        'openClose': True,
                        'change': 1  # Full sync
                    },
                    'completionProvider': {
                        'triggerCharacters': [' ', '.', '(', ':']
                    },
                    'hoverProvider': True,
                    'definitionProvider': True,
                    'referencesProvider': True,
                    'documentSymbolProvider': True,
                },
                'serverInfo': {
                    'name': 'CHILL Language Server',
                    'version': '1.0.0'
                }
            }
        }

    def _handle_did_open(self, params: Dict):
        """Handle textDocument/didOpen notification"""
        uri = params['textDocument']['uri']
        text = params['textDocument']['text']
        self.documents[uri] = text
        self._parse_document(uri)

    def _handle_did_change(self, params: Dict):
        """Handle textDocument/didChange notification"""
        uri = params['textDocument']['uri']
        changes = params['contentChanges']

        if changes:
            # Full sync - take last change
            self.documents[uri] = changes[-1].get('text', '')
            self._parse_document(uri)

    def _handle_did_close(self, params: Dict):
        """Handle textDocument/didClose notification"""
        uri = params['textDocument']['uri']
        if uri in self.documents:
            del self.documents[uri]
        if uri in self.models:
            del self.models[uri]

    def _parse_document(self, uri: str):
        """Parse a document and build semantic model"""
        if uri not in self.documents:
            return

        text = self.documents[uri]
        parser = ChillParser()
        model = parser.parse(text)
        self.models[uri] = model

    def _get_word_at_position(self, text: str, line: int, char: int) -> str:
        """Extract the word at a given position"""
        lines = text.split('\n')
        if line >= len(lines):
            return ''

        line_text = lines[line]
        if char > len(line_text):
            char = len(line_text)

        # Find word boundaries
        start = char
        while start > 0 and (line_text[start - 1].isalnum() or line_text[start - 1] == '_'):
            start -= 1

        end = char
        while end < len(line_text) and (line_text[end].isalnum() or line_text[end] == '_'):
            end += 1

        return line_text[start:end]

    def _handle_completion(self, request_id: Optional[int], params: Dict) -> Dict:
        """Handle textDocument/completion request"""
        uri = params['textDocument']['uri']
        position = LSPPosition.from_dict(params['position'])

        if uri not in self.documents:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {'isIncomplete': False, 'items': []}
            }

        model = self.models.get(uri, ChillSemanticModel())
        text = self.documents[uri]
        lines = text.split('\n')

        if position.line >= len(lines):
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {'isIncomplete': False, 'items': []}
            }

        line = lines[position.line]
        completions = get_completions_at_position(model, line, position.character)

        items = []
        for i, (name, kind_str) in enumerate(completions):
            # Determine LSP completion kind
            if kind_str == 'keyword':
                kind = 14  # Keyword
                detail = 'CHILL keyword'
            elif kind_str == 'builtin':
                kind = 3  # Function
                detail = 'Built-in function'
            elif kind_str == 'mode':
                kind = 7  # Class
                detail = 'NEWMODE'
            elif kind_str == 'procedure':
                kind = 3  # Function
                proc = model.procs.get(name)
                if proc:
                    params_str = ', '.join([f"{p[0]} {p[1]}" for p in proc.parameters])
                    detail = f'PROC({params_str})'
                else:
                    detail = 'PROC'
            elif kind_str == 'constant':
                kind = 21  # Constant
                syn = model.synonyms.get(name)
                detail = f'SYN = {syn.value}' if syn else 'SYN'
            elif kind_str.startswith('DCL'):
                kind = 6  # Variable
                detail = kind_str
            else:
                kind = 6  # Variable
                detail = kind_str

            items.append({
                'label': name,
                'kind': kind,
                'detail': detail,
                'insertText': name,
                'sortText': f'{i:04d}'
            })

        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'isIncomplete': False,
                'items': items
            }
        }

    def _handle_hover(self, request_id: Optional[int], params: Dict) -> Dict:
        """Handle textDocument/hover request"""
        uri = params['textDocument']['uri']
        position = LSPPosition.from_dict(params['position'])

        if uri not in self.documents:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': None
            }

        text = self.documents[uri]
        word = self._get_word_at_position(text, position.line, position.character)

        if not word:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': None
            }

        model = self.models.get(uri, ChillSemanticModel())

        # Try to get hover info from semantic model
        hover_info = get_hover_info(model, word)

        if hover_info:
            content = hover_info
        elif word.upper() in KEYWORD_DOCS:
            content = f"**{word}** - {KEYWORD_DOCS[word.upper()]}"
        else:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': None
            }

        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'contents': {
                    'kind': 'markdown',
                    'value': content
                }
            }
        }

    def _handle_definition(self, request_id: Optional[int], params: Dict) -> Dict:
        """Handle textDocument/definition request"""
        uri = params['textDocument']['uri']
        position = LSPPosition.from_dict(params['position'])

        if uri not in self.documents:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': None
            }

        text = self.documents[uri]
        word = self._get_word_at_position(text, position.line, position.character)

        if not word:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': None
            }

        model = self.models.get(uri, ChillSemanticModel())

        # Find definition line
        def_line = None

        # Check DCLs
        dcl = model.get_dcl(word)
        if dcl:
            def_line = dcl.line_number - 1  # Convert to 0-based

        # Check modes
        if def_line is None:
            mode = model.get_mode(word)
            if mode:
                def_line = mode.line_number - 1

        # Check procs
        if def_line is None:
            proc = model.get_proc(word)
            if proc:
                def_line = proc.line_start - 1

        # Check processes
        if def_line is None:
            process = model.processes.get(word)
            if process:
                def_line = process.line_start - 1

        # Check synonyms
        if def_line is None:
            syn = model.synonyms.get(word)
            if syn:
                def_line = syn.line_number - 1

        if def_line is None or def_line < 0:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': None
            }

        location = LSPLocation(
            uri=uri,
            range=LSPRange(
                start=LSPPosition(line=def_line, character=0),
                end=LSPPosition(line=def_line, character=100)
            )
        )

        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': location.to_dict()
        }

    def _handle_references(self, request_id: Optional[int], params: Dict) -> Dict:
        """Handle textDocument/references request"""
        uri = params['textDocument']['uri']
        position = LSPPosition.from_dict(params['position'])

        if uri not in self.documents:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': []
            }

        text = self.documents[uri]
        word = self._get_word_at_position(text, position.line, position.character)

        if not word:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': []
            }

        # Find all references
        references = []
        lines = text.split('\n')

        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)

        for i, line in enumerate(lines):
            for match in pattern.finditer(line):
                ref_range = LSPRange(
                    start=LSPPosition(line=i, character=match.start()),
                    end=LSPPosition(line=i, character=match.end())
                )
                references.append(LSPLocation(uri=uri, range=ref_range).to_dict())

        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': references
        }

    def _handle_document_symbol(self, request_id: Optional[int], params: Dict) -> Dict:
        """Handle textDocument/documentSymbol request"""
        uri = params['textDocument']['uri']

        if uri not in self.models:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': []
            }

        model = self.models[uri]
        symbols = []

        # Symbol kinds:
        # 2 = Module, 5 = Class, 6 = Method/Function, 12 = Function, 13 = Variable, 14 = Constant

        # Add modules
        for name, module in model.modules.items():
            symbols.append({
                'name': name,
                'kind': 2,  # Module
                'location': {
                    'uri': uri,
                    'range': {
                        'start': {'line': module.line_start - 1, 'character': 0},
                        'end': {'line': module.line_end - 1 if module.line_end else module.line_start - 1, 'character': 100}
                    }
                },
                'detail': 'MODULE'
            })

        # Add modes
        for name, mode in model.modes.items():
            symbols.append({
                'name': name,
                'kind': 5,  # Class
                'location': {
                    'uri': uri,
                    'range': {
                        'start': {'line': mode.line_number - 1, 'character': 0},
                        'end': {'line': mode.line_number - 1, 'character': 100}
                    }
                },
                'detail': f'NEWMODE {mode.base_mode.value}'
            })

        # Add DCLs (top-level only)
        seen = set()
        for name, dcl in model.dcls.items():
            if '.' not in name and name not in seen:
                seen.add(name)
                symbols.append({
                    'name': name,
                    'kind': 13,  # Variable
                    'location': {
                        'uri': uri,
                        'range': {
                            'start': {'line': dcl.line_number - 1, 'character': dcl.column_start},
                            'end': {'line': dcl.line_number - 1, 'character': dcl.column_end}
                        }
                    },
                    'detail': f'DCL {dcl.mode.value}'
                })

        # Add synonyms
        for name, syn in model.synonyms.items():
            symbols.append({
                'name': name,
                'kind': 14,  # Constant
                'location': {
                    'uri': uri,
                    'range': {
                        'start': {'line': syn.line_number - 1, 'character': 0},
                        'end': {'line': syn.line_number - 1, 'character': 100}
                    }
                },
                'detail': f'SYN = {syn.value}'
            })

        # Add procs
        for name, proc in model.procs.items():
            params_str = ', '.join([f"{p[0]} {p[1]}" for p in proc.parameters])
            symbols.append({
                'name': name,
                'kind': 12,  # Function
                'location': {
                    'uri': uri,
                    'range': {
                        'start': {'line': proc.line_start - 1, 'character': 0},
                        'end': {'line': proc.line_end - 1 if proc.line_end else proc.line_start - 1, 'character': 100}
                    }
                },
                'detail': f'PROC({params_str})'
            })

        # Add processes
        for name, process in model.processes.items():
            symbols.append({
                'name': name,
                'kind': 12,  # Function
                'location': {
                    'uri': uri,
                    'range': {
                        'start': {'line': process.line_start - 1, 'character': 0},
                        'end': {'line': process.line_end - 1 if process.line_end else process.line_start - 1, 'character': 100}
                    }
                },
                'detail': 'PROCESS'
            })

        # Add signals
        for name, sig in model.signals.items():
            symbols.append({
                'name': name,
                'kind': 24,  # Event
                'location': {
                    'uri': uri,
                    'range': {
                        'start': {'line': sig.line_number - 1, 'character': 0},
                        'end': {'line': sig.line_number - 1, 'character': 100}
                    }
                },
                'detail': 'SIGNAL'
            })

        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': symbols
        }


def main():
    """Main entry point for LSP server"""
    server = ChillLSPServer()

    while True:
        try:
            # Read header
            header = ""
            while True:
                char = sys.stdin.read(1)
                if not char:
                    return
                header += char
                if header.endswith('\r\n\r\n') or header.endswith('\n\n'):
                    break

            # Parse Content-Length header
            content_length = 0
            for line in header.split('\n'):
                if line.lower().startswith('content-length:'):
                    content_length = int(line.split(':')[1].strip())
                    break

            # Read message body
            if content_length > 0:
                message = sys.stdin.read(content_length)
                if not message:
                    break

                try:
                    request = json.loads(message)
                    response = server.handle_request(request)

                    if response:
                        response_json = json.dumps(response)
                        response_text = f"Content-Length: {len(response_json)}\r\n\r\n{response_json}"
                        sys.stdout.write(response_text)
                        sys.stdout.flush()

                except json.JSONDecodeError as e:
                    error_response = {
                        'jsonrpc': '2.0',
                        'error': {
                            'code': -32700,
                            'message': f'Parse error: {str(e)}'
                        }
                    }
                    error_json = json.dumps(error_response)
                    response_text = f"Content-Length: {len(error_json)}\r\n\r\n{error_json}"
                    sys.stdout.write(response_text)
                    sys.stdout.flush()

                except Exception as e:
                    error_response = {
                        'jsonrpc': '2.0',
                        'error': {
                            'code': -32603,
                            'message': f'Internal error: {str(e)}'
                        }
                    }
                    error_json = json.dumps(error_response)
                    response_text = f"Content-Length: {len(error_json)}\r\n\r\n{error_json}"
                    sys.stdout.write(response_text)
                    sys.stdout.flush()

        except Exception as e:
            sys.stderr.write(f"Fatal error: {str(e)}\n")
            sys.stderr.flush()
            break


if __name__ == '__main__':
    main()

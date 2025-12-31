"""
CHILL Semantic Parser - Builds AST and Semantic Model
Based on ITU-T Recommendation Z.200 (1999)

This parser builds a semantic model for CHILL code, enabling:
- DCL (variable) tracking and mode inference
- NEWMODE (type) definitions
- PROC (procedure) signatures
- PROCESS (concurrent process) definitions
- MODULE structure analysis
- Scope resolution for IDE features
"""

import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


class ChillMode(Enum):
    """CHILL data modes (types)"""
    INT = "INT"                 # Integer
    BOOL = "BOOL"               # Boolean
    CHAR = "CHAR"               # Character
    CHARS = "CHARS"             # Character string
    BOOLS = "BOOLS"             # Bit string
    SET = "SET"                 # Enumeration
    RANGE = "RANGE"             # Integer subrange
    POWERSET = "POWERSET"       # Set of discrete values
    REF = "REF"                 # Reference/pointer
    STRUCT = "STRUCT"           # Structure
    ARRAY = "ARRAY"             # Array
    PROC = "PROC"               # Procedure mode
    PROCESS = "PROCESS"         # Process mode
    BUFFER = "BUFFER"           # Buffer for inter-process communication
    EVENT = "EVENT"             # Synchronization event
    SIGNAL = "SIGNAL"           # Signal for inter-process communication
    ASSOCIATION = "ASSOCIATION" # File association
    ACCESS = "ACCESS"           # File access mode
    TEXT = "TEXT"               # Text I/O mode
    DURATION = "DURATION"       # Time duration
    TIME = "TIME"               # Absolute time
    USER_DEFINED = "USER"       # User-defined mode
    UNKNOWN = "UNKNOWN"


# Reserved words from ITU-T Z.200 Appendix III
CHILL_RESERVED_WORDS = {
    'ABSTRACT', 'ACCESS', 'AFTER', 'ALL', 'AND', 'ANDIF', 'ANY',
    'ARRAY', 'ASSERT', 'AT', 'BASED_ON', 'BEGIN', 'BIN', 'BODY',
    'BOOLS', 'BUFFER', 'BY', 'CASE', 'CAUSE', 'CHARS', 'CONTEXT',
    'CONTINUE', 'CYCLE', 'DCL', 'DELAY', 'DO', 'DOWN', 'DYNAMIC',
    'ELSE', 'ELSIF', 'END', 'ESAC', 'EVENT', 'EVER', 'EXCEPTIONS',
    'EXIT', 'FI', 'FINAL', 'FOR', 'FORBID', 'GENERAL', 'GENERIC',
    'GOTO', 'GRANT', 'IF', 'IMPLEMENTS', 'IN', 'INCOMPLETE', 'INIT',
    'INLINE', 'INOUT', 'INTERFACE', 'INVARIANT', 'LOC', 'MOD',
    'MODE', 'MODULE', 'NEW', 'NEWMODE', 'NONREF', 'NOPACK', 'NOT',
    'OD', 'OF', 'ON', 'OR', 'ORIF', 'OUT', 'PACK', 'POS', 'POST',
    'POWERSET', 'PRE', 'PREFIXED', 'PRIORITY', 'PROC', 'PROCESS',
    'RANGE', 'READ', 'RECEIVE', 'REF', 'REGION', 'REM', 'REMOTE',
    'RESULT', 'RETURN', 'RETURNS', 'ROW', 'SEIZE', 'SELF', 'SEND',
    'SET', 'SIGNAL', 'SIMPLE', 'SPEC', 'START', 'STATIC', 'STEP',
    'STOP', 'STRUCT', 'SYN', 'SYNMODE', 'TASK', 'TEXT', 'THEN',
    'THIS', 'TIMEOUT', 'TO', 'UP', 'VARYING', 'WCHARS', 'WHILE',
    'WITH', 'WTEXT', 'XOR', 'NOT_ASSIGNABLE', 'ANY_ASSIGN',
    'ANY_DISCRETE', 'ANY_INT', 'ANY_REAL', 'ASSIGNABLE', 'CONSTR',
    'DESTR', 'REIMPLEMENT'
}

# Predefined names from ITU-T Z.200 Appendix III.2
# Plus implementation-defined extensions commonly found in EWSD and other systems
CHILL_PREDEFINED = {
    # Built-in functions (III.2)
    'ABS', 'ABSTIME', 'ALLOCATE', 'ARCCOS', 'ARCSIN', 'ARCTAN',
    'ASSOCIATE', 'CARD', 'CONNECT', 'COS', 'CREATE', 'DELETE',
    'DISCONNECT', 'DISSOCIATE', 'EOLN', 'EXISTING', 'EXP', 'EXPIRED',
    'FIRST', 'FLOAT', 'GETASSOCIATION', 'GETSTACK', 'GETTEXTACCESS',
    'GETTEXTINDEX', 'GETTEXTRECORD', 'GETUSAGE', 'INDEXABLE',
    'INTTIME', 'ISASSOCIATED', 'LAST', 'LENGTH', 'LN', 'LOG', 'LOWER',
    'MAX', 'MIN', 'MODIFY', 'NUM', 'OUTOFFILE', 'PRED', 'PTR',
    'READABLE', 'READONLY', 'READRECORD', 'READTEXT', 'READWRITE',
    'SAME', 'SEQUENCIBLE', 'SETTEXTACCESS', 'SETTEXTINDEX',
    'SETTEXTRECORD', 'SIN', 'SIZE', 'SQRT', 'SUCC', 'TAN', 'TERMINATE',
    'UPPER', 'USAGE', 'VARIABLE', 'WAIT', 'WCHAR', 'WHERE',
    'WRITEABLE', 'WRITEONLY', 'WRITERECORD', 'WRITETEXT',
    # Built-in modes (III.2)
    'INT', 'BOOL', 'CHAR', 'DURATION', 'TIME', 'ASSOCIATION', 'INSTANCE',
    # Implementation-defined modes (common in EWSD, GCC CHILL)
    'BYTE', 'UBYTE', 'UINT', 'LONG', 'ULONG', 'REAL', 'LONG_REAL',
    # Constants (III.2)
    'TRUE', 'FALSE', 'NULL',
    # Time units (III.2)
    'DAYS', 'HOURS', 'MILLISECS', 'MINUTES', 'SECS',
    # Implementation-defined time units
    'SECONDS', 'MICROSECS'
}

# Operators
CHILL_OPERATORS = {
    # Arithmetic
    '+', '-', '*', '/', 'MOD', 'REM',
    # Relational
    '=', '/=', '<', '>', '<=', '>=',
    # Logical
    'AND', 'OR', 'XOR', 'NOT', 'ANDIF', 'ORIF',
    # Assignment
    ':=',
    # Other
    '->', '.', '^', '(', ')', '[', ']', ',', ';', ':'
}


@dataclass
class DclDefinition:
    """Represents a CHILL DCL (variable) declaration"""
    name: str
    mode: ChillMode
    mode_name: Optional[str] = None      # User-defined mode name
    size: Optional[int] = None           # For CHARS, BOOLS, ARRAY
    dimensions: List[Tuple[int, int]] = field(default_factory=list)  # Array bounds
    initial_value: Optional[str] = None
    is_static: bool = False
    is_dynamic: bool = False
    is_loc: bool = False                 # LOC (local) storage
    is_read: bool = False                # READ only
    line_number: int = 0
    column_start: int = 0
    column_end: int = 0
    parent_scope: Optional[str] = None


@dataclass
class NewmodeDefinition:
    """Represents a CHILL NEWMODE (type) definition"""
    name: str
    base_mode: ChillMode
    base_mode_name: Optional[str] = None
    fields: Dict[str, 'DclDefinition'] = field(default_factory=dict)  # For STRUCT
    enum_values: List[str] = field(default_factory=list)  # For SET
    range_low: Optional[int] = None      # For RANGE
    range_high: Optional[int] = None
    element_mode: Optional[str] = None   # For ARRAY
    dimensions: List[Tuple[int, int]] = field(default_factory=list)
    ref_mode: Optional[str] = None       # For REF
    is_packed: bool = False
    line_number: int = 0
    column_start: int = 0
    column_end: int = 0


@dataclass
class SynDefinition:
    """Represents a CHILL SYN (synonym/constant) definition"""
    name: str
    value: str
    mode: Optional[str] = None
    line_number: int = 0


@dataclass
class ProcDefinition:
    """Represents a CHILL PROC (procedure) definition"""
    name: str
    parameters: List[Tuple[str, str, str]] = field(default_factory=list)  # (name, mode, direction)
    returns_mode: Optional[str] = None
    is_general: bool = False             # GENERAL attribute
    is_inline: bool = False              # INLINE attribute
    is_recursive: bool = False
    exceptions: List[str] = field(default_factory=list)
    local_dcls: Dict[str, DclDefinition] = field(default_factory=dict)
    local_modes: Dict[str, NewmodeDefinition] = field(default_factory=dict)
    line_start: int = 0
    line_end: int = 0
    body_start: int = 0


@dataclass
class ProcessDefinition:
    """Represents a CHILL PROCESS definition"""
    name: str
    parameters: List[Tuple[str, str, str]] = field(default_factory=list)
    priority: Optional[int] = None
    local_dcls: Dict[str, DclDefinition] = field(default_factory=dict)
    local_modes: Dict[str, NewmodeDefinition] = field(default_factory=dict)
    line_start: int = 0
    line_end: int = 0


@dataclass
class ModuleDefinition:
    """Represents a CHILL MODULE"""
    name: str
    is_spec: bool = False                # SPEC MODULE
    is_body: bool = False                # Module body
    grants: List[str] = field(default_factory=list)      # GRANTed names
    seizes: List[str] = field(default_factory=list)      # SEIZEd names
    line_start: int = 0
    line_end: int = 0


@dataclass
class SignalDefinition:
    """Represents a CHILL SIGNAL definition"""
    name: str
    parameters: List[Tuple[str, str]] = field(default_factory=list)  # (name, mode)
    line_number: int = 0


class ChillSemanticModel:
    """
    Semantic model of a CHILL program
    Tracks DCLs, modes, procs, processes, modules, and scopes
    """

    def __init__(self):
        self.dcls: Dict[str, DclDefinition] = {}
        self.modes: Dict[str, NewmodeDefinition] = {}
        self.synonyms: Dict[str, SynDefinition] = {}
        self.procs: Dict[str, ProcDefinition] = {}
        self.processes: Dict[str, ProcessDefinition] = {}
        self.modules: Dict[str, ModuleDefinition] = {}
        self.signals: Dict[str, SignalDefinition] = {}
        self.regions: Dict[str, Any] = {}

        self.current_scope: str = "GLOBAL"
        self.scope_stack: List[str] = []
        self.module_name: Optional[str] = None

    def add_dcl(self, dcl: DclDefinition):
        """Add a DCL definition"""
        dcl.parent_scope = self.current_scope
        key = f"{self.current_scope}.{dcl.name}" if self.current_scope != "GLOBAL" else dcl.name
        self.dcls[dcl.name] = dcl
        self.dcls[key] = dcl

    def get_dcl(self, name: str) -> Optional[DclDefinition]:
        """Get DCL by name, checking scopes"""
        scoped_name = f"{self.current_scope}.{name}"
        if scoped_name in self.dcls:
            return self.dcls[scoped_name]
        if name in self.dcls:
            return self.dcls[name]
        return None

    def add_mode(self, mode: NewmodeDefinition):
        """Add a mode definition"""
        self.modes[mode.name] = mode

    def get_mode(self, name: str) -> Optional[NewmodeDefinition]:
        """Get mode by name"""
        return self.modes.get(name)

    def add_proc(self, proc: ProcDefinition):
        """Add a procedure definition"""
        self.procs[proc.name] = proc

    def get_proc(self, name: str) -> Optional[ProcDefinition]:
        """Get procedure by name"""
        return self.procs.get(name)

    def add_process(self, process: ProcessDefinition):
        """Add a process definition"""
        self.processes[process.name] = process

    def add_module(self, module: ModuleDefinition):
        """Add a module definition"""
        self.modules[module.name] = module

    def add_synonym(self, syn: SynDefinition):
        """Add a synonym definition"""
        self.synonyms[syn.name] = syn

    def add_signal(self, sig: SignalDefinition):
        """Add a signal definition"""
        self.signals[sig.name] = sig

    def push_scope(self, name: str):
        """Push a new scope"""
        self.scope_stack.append(self.current_scope)
        self.current_scope = name

    def pop_scope(self):
        """Pop current scope"""
        if self.scope_stack:
            self.current_scope = self.scope_stack.pop()

    def get_all_symbols(self) -> List[Tuple[str, str, int, int]]:
        """Get all symbols for document outline (name, kind, line, end_line)"""
        symbols = []

        for name, mode in self.modes.items():
            symbols.append((name, "MODE", mode.line_number, mode.line_number))

        for name, dcl in self.dcls.items():
            if '.' not in name:  # Skip scoped duplicates
                symbols.append((name, "DCL", dcl.line_number, dcl.line_number))

        for name, syn in self.synonyms.items():
            symbols.append((name, "SYN", syn.line_number, syn.line_number))

        for name, proc in self.procs.items():
            symbols.append((name, "PROC", proc.line_start, proc.line_end))

        for name, process in self.processes.items():
            symbols.append((name, "PROCESS", process.line_start, process.line_end))

        for name, module in self.modules.items():
            symbols.append((name, "MODULE", module.line_start, module.line_end))

        for name, sig in self.signals.items():
            symbols.append((name, "SIGNAL", sig.line_number, sig.line_number))

        return sorted(symbols, key=lambda x: x[2])


class ChillParser:
    """
    Parser for CHILL source code
    Builds a semantic model for IDE features
    """

    def __init__(self):
        self.model = ChillSemanticModel()
        self.lines: List[str] = []
        self.current_line = 0

    def parse(self, source: str) -> ChillSemanticModel:
        """Parse CHILL source and return semantic model"""
        self.model = ChillSemanticModel()
        self.lines = source.split('\n')
        self.current_line = 0

        # Remove comments and join continuation lines
        clean_lines = self._preprocess(source)

        # Parse declarations
        self._parse_declarations(clean_lines)

        return self.model

    def _preprocess(self, source: str) -> str:
        """Remove comments and normalize whitespace"""
        result = []

        # Remove /* */ comments
        source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)

        # Remove -- comments
        lines = source.split('\n')
        for line in lines:
            if '--' in line:
                line = line[:line.index('--')]
            result.append(line)

        return '\n'.join(result)

    def _parse_declarations(self, source: str):
        """Parse top-level declarations"""
        lines = source.split('\n')

        for i, line in enumerate(lines):
            line_num = i + 1
            stripped = line.strip().upper()

            # MODULE declaration
            if stripped.startswith('MODULE'):
                self._parse_module(stripped, line_num)

            # NEWMODE declaration
            elif stripped.startswith('NEWMODE') or stripped.startswith('SYNMODE'):
                self._parse_newmode(line.strip(), line_num)

            # DCL declaration
            elif stripped.startswith('DCL'):
                self._parse_dcl(line.strip(), line_num)

            # SYN declaration
            elif stripped.startswith('SYN'):
                self._parse_syn(line.strip(), line_num)

            # PROC declaration
            elif re.match(r'^[A-Z_][A-Z0-9_]*\s*:\s*PROC', stripped):
                self._parse_proc(line.strip(), line_num, lines, i)

            # PROCESS declaration
            elif re.match(r'^[A-Z_][A-Z0-9_]*\s*:\s*PROCESS', stripped):
                self._parse_process(line.strip(), line_num, lines, i)

            # SIGNAL declaration
            elif stripped.startswith('SIGNAL'):
                self._parse_signal(line.strip(), line_num)

    def _parse_module(self, line: str, line_num: int):
        """Parse MODULE declaration"""
        match = re.match(r'MODULE\s+([A-Z_][A-Z0-9_]*)', line, re.IGNORECASE)
        if match:
            name = match.group(1)
            is_spec = 'SPEC' in line.upper()
            module = ModuleDefinition(
                name=name,
                is_spec=is_spec,
                line_start=line_num
            )
            self.model.add_module(module)
            self.model.module_name = name
            self.model.push_scope(name)

    def _parse_newmode(self, line: str, line_num: int):
        """Parse NEWMODE or SYNMODE declaration"""
        # Match: NEWMODE name = mode_definition;
        match = re.match(
            r'(?:NEWMODE|SYNMODE)\s+([A-Z_][A-Z0-9_]*)\s*=\s*(.+)',
            line, re.IGNORECASE
        )
        if match:
            name = match.group(1)
            mode_def = match.group(2).rstrip(';').strip()

            mode = NewmodeDefinition(
                name=name,
                base_mode=self._infer_base_mode(mode_def),
                line_number=line_num
            )

            # Parse SET values
            set_match = re.match(r'SET\s*\(([^)]+)\)', mode_def, re.IGNORECASE)
            if set_match:
                mode.enum_values = [v.strip() for v in set_match.group(1).split(',')]

            # Parse RANGE
            range_match = re.match(r'RANGE\s*\(\s*(-?\d+)\s*:\s*(-?\d+)\s*\)', mode_def, re.IGNORECASE)
            if range_match:
                mode.range_low = int(range_match.group(1))
                mode.range_high = int(range_match.group(2))

            # Parse STRUCT fields
            struct_match = re.match(r'STRUCT\s*\((.+)\)', mode_def, re.IGNORECASE | re.DOTALL)
            if struct_match:
                self._parse_struct_fields(mode, struct_match.group(1))

            self.model.add_mode(mode)

    def _parse_struct_fields(self, mode: NewmodeDefinition, fields_str: str):
        """Parse STRUCT field definitions"""
        # Simple field parsing - could be enhanced
        fields = fields_str.split(',')
        for field in fields:
            field = field.strip()
            parts = field.split()
            if len(parts) >= 2:
                field_name = parts[0]
                field_mode = parts[-1] if len(parts) > 1 else 'UNKNOWN'
                mode.fields[field_name] = DclDefinition(
                    name=field_name,
                    mode=self._mode_str_to_enum(field_mode)
                )

    def _parse_dcl(self, line: str, line_num: int):
        """Parse DCL declaration"""
        # Match: DCL name mode [:= init];
        match = re.match(
            r'DCL\s+([A-Z_][A-Z0-9_]*)\s+([^:;]+)(?:\s*:=\s*([^;]+))?\s*;?',
            line, re.IGNORECASE
        )
        if match:
            name = match.group(1)
            mode_str = match.group(2).strip()
            init_value = match.group(3).strip() if match.group(3) else None

            dcl = DclDefinition(
                name=name,
                mode=self._mode_str_to_enum(mode_str),
                mode_name=mode_str if not self._is_builtin_mode(mode_str) else None,
                initial_value=init_value,
                is_static='STATIC' in mode_str.upper(),
                line_number=line_num,
                column_start=line.upper().find(name.upper()),
                column_end=line.upper().find(name.upper()) + len(name)
            )
            self.model.add_dcl(dcl)

    def _parse_syn(self, line: str, line_num: int):
        """Parse SYN declaration"""
        # Match: SYN name [mode] = value;
        match = re.match(
            r'SYN\s+([A-Z_][A-Z0-9_]*)(?:\s+([A-Z_][A-Z0-9_]*))?\s*=\s*([^;]+)\s*;?',
            line, re.IGNORECASE
        )
        if match:
            syn = SynDefinition(
                name=match.group(1),
                mode=match.group(2),
                value=match.group(3).strip(),
                line_number=line_num
            )
            self.model.add_synonym(syn)

    def _parse_proc(self, line: str, line_num: int, all_lines: List[str], start_idx: int):
        """Parse PROC declaration"""
        match = re.match(
            r'([A-Z_][A-Z0-9_]*)\s*:\s*PROC\s*(?:\(([^)]*)\))?\s*(?:RETURNS\s*\(([^)]+)\))?',
            line, re.IGNORECASE
        )
        if match:
            name = match.group(1)
            params_str = match.group(2)
            returns = match.group(3)

            proc = ProcDefinition(
                name=name,
                returns_mode=returns.strip() if returns else None,
                is_general='GENERAL' in line.upper(),
                line_start=line_num
            )

            # Parse parameters
            if params_str:
                proc.parameters = self._parse_parameters(params_str)

            # Find END
            proc.line_end = self._find_end(all_lines, start_idx, 'PROC')

            self.model.add_proc(proc)

    def _parse_process(self, line: str, line_num: int, all_lines: List[str], start_idx: int):
        """Parse PROCESS declaration"""
        match = re.match(
            r'([A-Z_][A-Z0-9_]*)\s*:\s*PROCESS\s*(?:\(([^)]*)\))?',
            line, re.IGNORECASE
        )
        if match:
            name = match.group(1)
            params_str = match.group(2)

            process = ProcessDefinition(
                name=name,
                line_start=line_num
            )

            if params_str:
                process.parameters = self._parse_parameters(params_str)

            process.line_end = self._find_end(all_lines, start_idx, 'PROCESS')

            self.model.add_process(process)

    def _parse_signal(self, line: str, line_num: int):
        """Parse SIGNAL declaration"""
        match = re.match(
            r'SIGNAL\s+([A-Z_][A-Z0-9_]*)(?:\s*\(([^)]*)\))?\s*;?',
            line, re.IGNORECASE
        )
        if match:
            name = match.group(1)
            params_str = match.group(2)

            signal = SignalDefinition(
                name=name,
                line_number=line_num
            )

            if params_str:
                for param in params_str.split(','):
                    parts = param.strip().split()
                    if len(parts) >= 2:
                        signal.parameters.append((parts[0], parts[-1]))

            self.model.add_signal(signal)

    def _parse_parameters(self, params_str: str) -> List[Tuple[str, str, str]]:
        """Parse procedure/process parameters"""
        params = []
        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue

            direction = 'IN'
            if 'INOUT' in param.upper():
                direction = 'INOUT'
                param = re.sub(r'\bINOUT\b', '', param, flags=re.IGNORECASE)
            elif 'OUT' in param.upper():
                direction = 'OUT'
                param = re.sub(r'\bOUT\b', '', param, flags=re.IGNORECASE)
            elif 'IN' in param.upper():
                param = re.sub(r'\bIN\b', '', param, flags=re.IGNORECASE)

            parts = param.strip().split()
            if len(parts) >= 2:
                params.append((parts[0], parts[-1], direction))
            elif len(parts) == 1:
                params.append((parts[0], 'UNKNOWN', direction))

        return params

    def _find_end(self, lines: List[str], start_idx: int, construct: str) -> int:
        """Find matching END for a construct"""
        depth = 1
        for i in range(start_idx + 1, len(lines)):
            line = lines[i].strip().upper()

            # Count nested constructs
            if re.match(r'^[A-Z_][A-Z0-9_]*\s*:\s*(PROC|PROCESS|MODULE|REGION)', line):
                depth += 1
            elif line.startswith('BEGIN'):
                depth += 1
            elif line.startswith('END'):
                depth -= 1
                if depth == 0:
                    return i + 1

        return start_idx + 1

    def _infer_base_mode(self, mode_str: str) -> ChillMode:
        """Infer the base mode from a mode string"""
        mode_upper = mode_str.upper().strip()

        if mode_upper.startswith('SET'):
            return ChillMode.SET
        elif mode_upper.startswith('RANGE'):
            return ChillMode.RANGE
        elif mode_upper.startswith('STRUCT'):
            return ChillMode.STRUCT
        elif mode_upper.startswith('ARRAY'):
            return ChillMode.ARRAY
        elif mode_upper.startswith('REF'):
            return ChillMode.REF
        elif mode_upper.startswith('POWERSET'):
            return ChillMode.POWERSET
        elif mode_upper.startswith('CHARS'):
            return ChillMode.CHARS
        elif mode_upper.startswith('BOOLS'):
            return ChillMode.BOOLS
        elif mode_upper.startswith('PROC'):
            return ChillMode.PROC
        elif mode_upper.startswith('BUFFER'):
            return ChillMode.BUFFER
        elif mode_upper.startswith('EVENT'):
            return ChillMode.EVENT
        elif mode_upper.startswith('SIGNAL'):
            return ChillMode.SIGNAL
        else:
            return self._mode_str_to_enum(mode_upper)

    def _mode_str_to_enum(self, mode_str: str) -> ChillMode:
        """Convert mode string to ChillMode enum"""
        mode_upper = mode_str.upper().strip().split()[0] if mode_str else 'UNKNOWN'

        mode_map = {
            'INT': ChillMode.INT,
            'BOOL': ChillMode.BOOL,
            'CHAR': ChillMode.CHAR,
            'CHARS': ChillMode.CHARS,
            'BOOLS': ChillMode.BOOLS,
            'SET': ChillMode.SET,
            'RANGE': ChillMode.RANGE,
            'POWERSET': ChillMode.POWERSET,
            'REF': ChillMode.REF,
            'STRUCT': ChillMode.STRUCT,
            'ARRAY': ChillMode.ARRAY,
            'PROC': ChillMode.PROC,
            'PROCESS': ChillMode.PROCESS,
            'BUFFER': ChillMode.BUFFER,
            'EVENT': ChillMode.EVENT,
            'SIGNAL': ChillMode.SIGNAL,
            'ASSOCIATION': ChillMode.ASSOCIATION,
            'ACCESS': ChillMode.ACCESS,
            'TEXT': ChillMode.TEXT,
            'DURATION': ChillMode.DURATION,
            'TIME': ChillMode.TIME,
            'BYTE': ChillMode.INT,
            'UBYTE': ChillMode.INT,
            'UINT': ChillMode.INT,
            'LONG': ChillMode.INT,
            'ULONG': ChillMode.INT,
            'REAL': ChillMode.INT,
            'LONG_REAL': ChillMode.INT,
        }

        return mode_map.get(mode_upper, ChillMode.USER_DEFINED)

    def _is_builtin_mode(self, mode_str: str) -> bool:
        """Check if mode is a built-in mode"""
        return mode_str.upper().split()[0] in {
            'INT', 'BOOL', 'CHAR', 'CHARS', 'BOOLS', 'BYTE', 'UBYTE',
            'UINT', 'LONG', 'ULONG', 'REAL', 'LONG_REAL', 'DURATION',
            'TIME', 'ASSOCIATION', 'INSTANCE'
        }


def get_completions_at_position(model: ChillSemanticModel, line: str, column: int) -> List[Tuple[str, str]]:
    """Get completion suggestions at cursor position"""
    completions = []

    # Get word prefix
    prefix = ''
    for i in range(column - 1, -1, -1):
        if i < len(line) and (line[i].isalnum() or line[i] == '_'):
            prefix = line[i] + prefix
        else:
            break

    prefix_upper = prefix.upper()

    # Add matching keywords
    for kw in CHILL_RESERVED_WORDS:
        if kw.startswith(prefix_upper):
            completions.append((kw, 'keyword'))

    # Add matching predefined names
    for pred in CHILL_PREDEFINED:
        if pred.startswith(prefix_upper):
            completions.append((pred, 'builtin'))

    # Add matching DCLs
    for name, dcl in model.dcls.items():
        if '.' not in name and name.upper().startswith(prefix_upper):
            completions.append((name, f"DCL {dcl.mode.value}"))

    # Add matching modes
    for name in model.modes:
        if name.upper().startswith(prefix_upper):
            completions.append((name, 'mode'))

    # Add matching procs
    for name in model.procs:
        if name.upper().startswith(prefix_upper):
            completions.append((name, 'procedure'))

    # Add matching synonyms
    for name in model.synonyms:
        if name.upper().startswith(prefix_upper):
            completions.append((name, 'constant'))

    return completions


def get_hover_info(model: ChillSemanticModel, word: str) -> Optional[str]:
    """Get hover information for a word"""
    word_upper = word.upper()

    # Check reserved words
    if word_upper in CHILL_RESERVED_WORDS:
        return f"**{word}** - CHILL reserved word"

    # Check predefined
    if word_upper in CHILL_PREDEFINED:
        return f"**{word}** - CHILL predefined name"

    # Check DCLs
    dcl = model.get_dcl(word)
    if dcl:
        info = f"**{word}** - DCL {dcl.mode.value}"
        if dcl.mode_name:
            info += f" ({dcl.mode_name})"
        if dcl.initial_value:
            info += f"\n\nInitial value: {dcl.initial_value}"
        return info

    # Check modes
    mode = model.get_mode(word)
    if mode:
        info = f"**{word}** - NEWMODE {mode.base_mode.value}"
        if mode.enum_values:
            info += f"\n\nValues: {', '.join(mode.enum_values)}"
        if mode.range_low is not None:
            info += f"\n\nRange: {mode.range_low}:{mode.range_high}"
        if mode.fields:
            info += f"\n\nFields: {', '.join(mode.fields.keys())}"
        return info

    # Check procs
    proc = model.get_proc(word)
    if proc:
        params = ', '.join([f"{p[0]} {p[2]} {p[1]}" for p in proc.parameters])
        info = f"**{word}** - PROC({params})"
        if proc.returns_mode:
            info += f" RETURNS({proc.returns_mode})"
        return info

    # Check synonyms
    syn = model.synonyms.get(word)
    if syn:
        return f"**{word}** - SYN = {syn.value}"

    return None


if __name__ == "__main__":
    # Test the parser
    test_code = """
    MODULE example;

    NEWMODE counter = RANGE(0:65535);
    NEWMODE status = SET(idle, active, error);
    NEWMODE point = STRUCT(x INT, y INT);

    SYN max_size = 100;

    DCL count counter := 0;
    DCL state status := idle;
    DCL position point;

    handler: PROC(input INT) RETURNS(INT);
      DCL result INT;
      result := input * 2;
      RETURN result;
    END handler;

    worker: PROCESS(id INT);
      DO WHILE TRUE;
        DELAY 1 SECONDS;
      OD;
    END worker;

    END example;
    """

    parser = ChillParser()
    model = parser.parse(test_code)

    print("=== CHILL Semantic Model ===")
    print(f"\nModules: {list(model.modules.keys())}")
    print(f"Modes: {list(model.modes.keys())}")
    print(f"DCLs: {[k for k in model.dcls.keys() if '.' not in k]}")
    print(f"Synonyms: {list(model.synonyms.keys())}")
    print(f"Procs: {list(model.procs.keys())}")
    print(f"Processes: {list(model.processes.keys())}")

    print("\n=== Hover Info ===")
    print(get_hover_info(model, "counter"))
    print(get_hover_info(model, "status"))
    print(get_hover_info(model, "handler"))

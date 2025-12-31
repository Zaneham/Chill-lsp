"""
CHILL AST Node Definitions
Based on ITU-T Recommendation Z.200 (1999)

These nodes represent the abstract syntax tree for CHILL programs.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Union
from enum import Enum, auto


class NodeType(Enum):
    """Categories of AST nodes"""
    PROGRAM = auto()
    MODULE = auto()
    PROCEDURE = auto()
    PROCESS = auto()
    REGION = auto()

    # Declarations
    DCL = auto()
    NEWMODE = auto()
    SYNMODE = auto()
    SYN = auto()
    SIGNAL = auto()

    # Modes (types)
    MODE_INT = auto()
    MODE_BOOL = auto()
    MODE_CHAR = auto()
    MODE_CHARS = auto()
    MODE_BOOLS = auto()
    MODE_SET = auto()
    MODE_RANGE = auto()
    MODE_POWERSET = auto()
    MODE_REF = auto()
    MODE_STRUCT = auto()
    MODE_ARRAY = auto()
    MODE_PROC = auto()
    MODE_BUFFER = auto()
    MODE_EVENT = auto()
    MODE_DURATION = auto()
    MODE_TIME = auto()
    MODE_NAMED = auto()

    # Statements
    ASSIGN = auto()
    IF = auto()
    CASE = auto()
    DO_WHILE = auto()
    DO_FOR = auto()
    DO_EVER = auto()
    EXIT = auto()
    RETURN = auto()
    RESULT = auto()
    GOTO = auto()
    CALL = auto()
    SEND = auto()
    RECEIVE = auto()
    DELAY = auto()
    START = auto()
    STOP = auto()
    CONTINUE = auto()
    ASSERT = auto()
    CAUSE = auto()

    # Expressions
    BINARY_OP = auto()
    UNARY_OP = auto()
    LITERAL = auto()
    IDENTIFIER = auto()
    ARRAY_ACCESS = auto()
    FIELD_ACCESS = auto()
    PROC_CALL = auto()
    SLICE = auto()

    # Other
    LABEL = auto()
    GRANT = auto()
    SEIZE = auto()
    HANDLER = auto()


@dataclass
class SourceLocation:
    """Source code location for error reporting"""
    line: int
    column: int
    filename: str = "<unknown>"


@dataclass(kw_only=True)
class ASTNode:
    """Base class for all AST nodes"""
    location: Optional[SourceLocation] = None

    def accept(self, visitor):
        """Visitor pattern for tree traversal"""
        method_name = f'visit_{self.__class__.__name__}'
        visitor_method = getattr(visitor, method_name, visitor.generic_visit)
        return visitor_method(self)


# ============================================================================
# Mode (Type) Nodes
# ============================================================================

@dataclass(kw_only=True)
class ModeNode(ASTNode):
    """Base class for mode (type) nodes"""
    pass


@dataclass(kw_only=True)
class IntMode(ModeNode):
    """INT mode"""
    pass


@dataclass(kw_only=True)
class BoolMode(ModeNode):
    """BOOL mode"""
    pass


@dataclass(kw_only=True)
class CharMode(ModeNode):
    """CHAR mode"""
    pass


@dataclass(kw_only=True)
class CharsMode(ModeNode):
    """CHARS(n) - character string mode"""
    length: 'Expression'
    varying: bool = False


@dataclass(kw_only=True)
class BoolsMode(ModeNode):
    """BOOLS(n) - bit string mode"""
    length: 'Expression'


@dataclass(kw_only=True)
class SetMode(ModeNode):
    """SET(a, b, c) - enumeration mode"""
    elements: List[str] = field(default_factory=list)


@dataclass(kw_only=True)
class RangeMode(ModeNode):
    """RANGE(lower:upper) - integer subrange mode"""
    lower: 'Expression'
    upper: 'Expression'


@dataclass(kw_only=True)
class PowersetMode(ModeNode):
    """POWERSET mode - set of discrete values"""
    base_mode: ModeNode


@dataclass(kw_only=True)
class RefMode(ModeNode):
    """REF mode - reference/pointer"""
    target_mode: ModeNode
    free: bool = False  # FREE REF vs bound REF


@dataclass(kw_only=True)
class StructField(ASTNode):
    """Field in a STRUCT"""
    names: List[str]
    mode: ModeNode


@dataclass(kw_only=True)
class StructMode(ModeNode):
    """STRUCT mode - record type"""
    fields: List[StructField] = field(default_factory=list)


@dataclass(kw_only=True)
class ArrayMode(ModeNode):
    """ARRAY mode"""
    index_mode: ModeNode  # Usually a range
    element_mode: ModeNode
    layout: Optional[str] = None  # PACK, NOPACK


@dataclass(kw_only=True)
class ProcMode(ModeNode):
    """PROC mode - procedure type"""
    parameters: List['Parameter'] = field(default_factory=list)
    returns: Optional[ModeNode] = None
    exceptions: List[str] = field(default_factory=list)


@dataclass(kw_only=True)
class BufferMode(ModeNode):
    """BUFFER mode - for inter-process communication"""
    size: 'Expression'
    element_mode: ModeNode


@dataclass(kw_only=True)
class EventMode(ModeNode):
    """EVENT mode - synchronization primitive"""
    pass


@dataclass(kw_only=True)
class DurationMode(ModeNode):
    """DURATION mode - time duration"""
    pass


@dataclass(kw_only=True)
class TimeMode(ModeNode):
    """TIME mode - absolute time"""
    pass


@dataclass(kw_only=True)
class NamedMode(ModeNode):
    """Reference to a named mode (user-defined type)"""
    name: str


# ============================================================================
# Declaration Nodes
# ============================================================================

@dataclass(kw_only=True)
class Parameter(ASTNode):
    """Procedure/process parameter"""
    name: str
    mode: ModeNode
    param_mode: str = "IN"  # IN, OUT, INOUT, LOC


@dataclass(kw_only=True)
class DclNode(ASTNode):
    """DCL - variable declaration"""
    names: List[str]
    mode: ModeNode
    init: Optional['Expression'] = None
    static: bool = False
    read_only: bool = False


@dataclass(kw_only=True)
class NewmodeNode(ASTNode):
    """NEWMODE - type definition"""
    name: str
    mode: ModeNode


@dataclass(kw_only=True)
class SynmodeNode(ASTNode):
    """SYNMODE - type alias"""
    name: str
    mode: ModeNode


@dataclass(kw_only=True)
class SynNode(ASTNode):
    """SYN - named constant"""
    name: str
    value: 'Expression'
    mode: Optional[ModeNode] = None


@dataclass(kw_only=True)
class SignalNode(ASTNode):
    """SIGNAL definition for inter-process communication"""
    name: str
    parameters: List[Parameter] = field(default_factory=list)
    destination: Optional[str] = None


# ============================================================================
# Expression Nodes
# ============================================================================

@dataclass(kw_only=True)
class Expression(ASTNode):
    """Base class for expressions"""
    pass


@dataclass(kw_only=True)
class Literal(Expression):
    """Literal value"""
    value: Any
    kind: str  # 'int', 'bool', 'char', 'string', 'null', 'duration'


@dataclass(kw_only=True)
class Identifier(Expression):
    """Variable/constant reference"""
    name: str


@dataclass(kw_only=True)
class BinaryOp(Expression):
    """Binary operation"""
    op: str  # +, -, *, /, MOD, REM, AND, OR, XOR, =, /=, <, >, <=, >=, //, IN
    left: Expression
    right: Expression


@dataclass(kw_only=True)
class UnaryOp(Expression):
    """Unary operation"""
    op: str  # NOT, -, +
    operand: Expression


@dataclass(kw_only=True)
class ArrayAccess(Expression):
    """Array/string indexing: arr(i) or arr(i:j)"""
    array: Expression
    index: Expression


@dataclass(kw_only=True)
class SliceAccess(Expression):
    """Array/string slicing: arr(i:j)"""
    array: Expression
    start: Expression
    end: Expression


@dataclass(kw_only=True)
class FieldAccess(Expression):
    """Structure field access: s.field"""
    struct: Expression
    field: str


@dataclass(kw_only=True)
class DerefAccess(Expression):
    """Pointer dereference: ptr->"""
    ref: Expression


@dataclass(kw_only=True)
class ProcCall(Expression):
    """Procedure call (as expression)"""
    proc: Expression
    arguments: List[Expression] = field(default_factory=list)


@dataclass(kw_only=True)
class StartExpr(Expression):
    """START expression - creates a new process"""
    process: str
    arguments: List[Expression] = field(default_factory=list)


@dataclass(kw_only=True)
class ReceiveExpr(Expression):
    """RECEIVE expression"""
    buffer: Expression


@dataclass(kw_only=True)
class BuiltinCall(Expression):
    """Built-in function call (ABS, LENGTH, SIZE, etc.)"""
    name: str
    arguments: List[Expression] = field(default_factory=list)


@dataclass(kw_only=True)
class IfExpr(Expression):
    """IF expression (conditional expression)"""
    condition: Expression
    then_expr: Expression
    else_expr: Expression


@dataclass(kw_only=True)
class CaseExpr(Expression):
    """CASE expression"""
    selector: Expression
    alternatives: List['CaseAlternative']
    else_expr: Optional[Expression] = None


# ============================================================================
# Statement Nodes
# ============================================================================

@dataclass(kw_only=True)
class Statement(ASTNode):
    """Base class for statements"""
    label: Optional[str] = None


@dataclass(kw_only=True)
class AssignStmt(Statement):
    """Assignment: location := value"""
    targets: List[Expression]
    value: Expression


@dataclass(kw_only=True)
class IfStmt(Statement):
    """IF-THEN-ELSIF-ELSE-FI"""
    condition: Expression
    then_stmts: List[Statement]
    elsif_parts: List['ElsifPart'] = field(default_factory=list)
    else_stmts: List[Statement] = field(default_factory=list)


@dataclass(kw_only=True)
class ElsifPart(ASTNode):
    """ELSIF clause"""
    condition: Expression
    statements: List[Statement]


@dataclass(kw_only=True)
class CaseAlternative(ASTNode):
    """Case alternative: (values): statements"""
    values: List[Expression]
    statements: List[Statement]


@dataclass(kw_only=True)
class CaseStmt(Statement):
    """CASE-OF-ESAC"""
    selector: Expression
    alternatives: List[CaseAlternative]
    else_stmts: List[Statement] = field(default_factory=list)


@dataclass(kw_only=True)
class DoWhileStmt(Statement):
    """DO WHILE condition; ... OD"""
    condition: Expression
    statements: List[Statement]


@dataclass(kw_only=True)
class DoForStmt(Statement):
    """DO FOR i := start TO end BY step; ... OD"""
    var: str
    start: Expression
    end: Expression
    step: Optional[Expression] = None
    down: bool = False  # DOWN TO
    statements: List[Statement] = field(default_factory=list)


@dataclass(kw_only=True)
class DoEverStmt(Statement):
    """DO EVER; ... OD (infinite loop)"""
    statements: List[Statement]


@dataclass(kw_only=True)
class ExitStmt(Statement):
    """EXIT label"""
    target: Optional[str] = None


@dataclass(kw_only=True)
class ReturnStmt(Statement):
    """RETURN or RETURN value"""
    value: Optional[Expression] = None


@dataclass(kw_only=True)
class ResultStmt(Statement):
    """RESULT value"""
    value: Expression


@dataclass(kw_only=True)
class GotoStmt(Statement):
    """GOTO label"""
    target: str


@dataclass(kw_only=True)
class CallStmt(Statement):
    """Procedure call (as statement)"""
    proc: Expression
    arguments: List[Expression] = field(default_factory=list)


@dataclass(kw_only=True)
class SendStmt(Statement):
    """SEND signal TO process or SEND value TO buffer"""
    signal: str
    arguments: List[Expression] = field(default_factory=list)
    destination: Optional[Expression] = None


@dataclass(kw_only=True)
class ReceiveCaseStmt(Statement):
    """RECEIVE CASE for signals/buffers"""
    alternatives: List['ReceiveAlternative']
    else_stmts: List[Statement] = field(default_factory=list)


@dataclass(kw_only=True)
class ReceiveAlternative(ASTNode):
    """Alternative in RECEIVE CASE"""
    signal: str
    parameters: List[str] = field(default_factory=list)
    statements: List[Statement] = field(default_factory=list)


@dataclass(kw_only=True)
class DelayStmt(Statement):
    """DELAY duration or DELAY CASE"""
    duration: Optional[Expression] = None


@dataclass(kw_only=True)
class StartStmt(Statement):
    """START process(args)"""
    process: str
    arguments: List[Expression] = field(default_factory=list)


@dataclass(kw_only=True)
class StopStmt(Statement):
    """STOP - terminate current process"""
    pass


@dataclass(kw_only=True)
class ContinueStmt(Statement):
    """CONTINUE event"""
    event: Expression


@dataclass(kw_only=True)
class AssertStmt(Statement):
    """ASSERT condition"""
    condition: Expression


@dataclass(kw_only=True)
class CauseStmt(Statement):
    """CAUSE exception"""
    exception: str


@dataclass(kw_only=True)
class EmptyStmt(Statement):
    """Empty statement (;)"""
    pass


@dataclass(kw_only=True)
class BeginEndBlock(Statement):
    """BEGIN ... END block"""
    declarations: List[ASTNode] = field(default_factory=list)
    statements: List[Statement] = field(default_factory=list)


# ============================================================================
# Program Structure Nodes
# ============================================================================

@dataclass(kw_only=True)
class ProcDef(ASTNode):
    """Procedure definition"""
    name: str
    parameters: List[Parameter] = field(default_factory=list)
    returns: Optional[ModeNode] = None
    result_loc: bool = False  # RETURNS vs LOC RETURNS
    exceptions: List[str] = field(default_factory=list)
    declarations: List[ASTNode] = field(default_factory=list)
    statements: List[Statement] = field(default_factory=list)
    is_recursive: bool = False
    is_inline: bool = False
    is_general: bool = False


@dataclass(kw_only=True)
class ProcessDef(ASTNode):
    """Process definition"""
    name: str
    parameters: List[Parameter] = field(default_factory=list)
    declarations: List[ASTNode] = field(default_factory=list)
    statements: List[Statement] = field(default_factory=list)
    priority: Optional[Expression] = None


@dataclass(kw_only=True)
class RegionDef(ASTNode):
    """Region definition (mutual exclusion)"""
    name: str
    declarations: List[ASTNode] = field(default_factory=list)
    procs: List[ProcDef] = field(default_factory=list)


@dataclass(kw_only=True)
class ModuleDef(ASTNode):
    """Module definition"""
    name: str
    declarations: List[ASTNode] = field(default_factory=list)
    procs: List[ProcDef] = field(default_factory=list)
    processes: List[ProcessDef] = field(default_factory=list)
    regions: List[RegionDef] = field(default_factory=list)
    grants: List[str] = field(default_factory=list)
    seizes: List[str] = field(default_factory=list)


@dataclass(kw_only=True)
class Program(ASTNode):
    """Complete CHILL program"""
    modules: List[ModuleDef] = field(default_factory=list)
    declarations: List[ASTNode] = field(default_factory=list)  # Top-level

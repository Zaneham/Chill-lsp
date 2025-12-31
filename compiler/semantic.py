"""
CHILL Semantic Analyzer
Type checking and symbol table management

Based on ITU-T Z.200 (1999) type rules.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Union
from enum import Enum, auto

# Support both relative and absolute imports
try:
    from .ast_nodes import *
except ImportError:
    from ast_nodes import *


class SemanticError(Exception):
    """Semantic analysis error"""
    def __init__(self, message: str, location: Optional[SourceLocation] = None):
        self.message = message
        self.location = location
        if location:
            super().__init__(f"{message} at line {location.line}, column {location.column}")
        else:
            super().__init__(message)


class TypeKind(Enum):
    """Categories of CHILL types"""
    INT = auto()
    BOOL = auto()
    CHAR = auto()
    CHARS = auto()
    BOOLS = auto()
    SET = auto()
    RANGE = auto()
    POWERSET = auto()
    REF = auto()
    STRUCT = auto()
    ARRAY = auto()
    PROC = auto()
    BUFFER = auto()
    EVENT = auto()
    DURATION = auto()
    TIME = auto()
    VOID = auto()
    ERROR = auto()  # For error recovery


@dataclass
class Type:
    """Represents a resolved type"""
    kind: TypeKind
    name: Optional[str] = None  # For named types

    def __eq__(self, other):
        if not isinstance(other, Type):
            return False
        return self.kind == other.kind

    def __hash__(self):
        return hash(self.kind)


@dataclass
class IntType(Type):
    """Integer type with optional range"""
    kind: TypeKind = TypeKind.INT
    lower: Optional[int] = None
    upper: Optional[int] = None


@dataclass
class CharsType(Type):
    """Character string type"""
    kind: TypeKind = TypeKind.CHARS
    length: int = 0
    varying: bool = False


@dataclass
class BoolsType(Type):
    """Bit string type"""
    kind: TypeKind = TypeKind.BOOLS
    length: int = 0


@dataclass
class SetType(Type):
    """Enumeration type"""
    kind: TypeKind = TypeKind.SET
    elements: List[str] = field(default_factory=list)


@dataclass
class RangeType(Type):
    """Integer subrange type"""
    kind: TypeKind = TypeKind.RANGE
    lower: int = 0
    upper: int = 0


@dataclass
class RefType(Type):
    """Reference/pointer type"""
    kind: TypeKind = TypeKind.REF
    target: Optional[Type] = None
    free: bool = False


@dataclass
class StructField:
    """Field in a struct type"""
    name: str
    type: Type


@dataclass
class StructType(Type):
    """Structure type"""
    kind: TypeKind = TypeKind.STRUCT
    fields: List[StructField] = field(default_factory=list)


@dataclass
class ArrayType(Type):
    """Array type"""
    kind: TypeKind = TypeKind.ARRAY
    index_type: Type = None
    element_type: Type = None


@dataclass
class ParamInfo:
    """Parameter information for procedures"""
    name: str
    type: Type
    mode: str = "IN"  # IN, OUT, INOUT, LOC


@dataclass
class ProcType(Type):
    """Procedure type"""
    kind: TypeKind = TypeKind.PROC
    params: List[ParamInfo] = field(default_factory=list)
    returns: Optional[Type] = None


@dataclass
class BufferType(Type):
    """Buffer type for IPC"""
    kind: TypeKind = TypeKind.BUFFER
    size: int = 0
    element_type: Type = None


# Singleton types
BOOL_TYPE = Type(kind=TypeKind.BOOL)
CHAR_TYPE = Type(kind=TypeKind.CHAR)
INT_TYPE = IntType()
DURATION_TYPE = Type(kind=TypeKind.DURATION)
TIME_TYPE = Type(kind=TypeKind.TIME)
EVENT_TYPE = Type(kind=TypeKind.EVENT)
VOID_TYPE = Type(kind=TypeKind.VOID)
ERROR_TYPE = Type(kind=TypeKind.ERROR)


@dataclass
class Symbol:
    """Symbol table entry"""
    name: str
    kind: str  # 'variable', 'type', 'proc', 'process', 'signal', 'constant'
    type: Type
    location: Optional[SourceLocation] = None
    is_static: bool = False
    is_readonly: bool = False


class Scope:
    """A scope in the symbol table"""

    def __init__(self, name: str, parent: Optional['Scope'] = None):
        self.name = name
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self.children: List['Scope'] = []

    def define(self, symbol: Symbol) -> bool:
        """Add symbol to this scope, return False if already defined"""
        upper_name = symbol.name.upper()
        if upper_name in self.symbols:
            return False
        self.symbols[upper_name] = symbol
        return True

    def lookup(self, name: str, local_only: bool = False) -> Optional[Symbol]:
        """Look up a symbol, searching parent scopes if not local_only"""
        upper_name = name.upper()
        if upper_name in self.symbols:
            return self.symbols[upper_name]
        if not local_only and self.parent:
            return self.parent.lookup(upper_name)
        return None

    def enter_scope(self, name: str) -> 'Scope':
        """Create and enter a child scope"""
        child = Scope(name, parent=self)
        self.children.append(child)
        return child


class SemanticAnalyzer:
    """
    Semantic analyzer for CHILL

    Performs:
    - Symbol table construction
    - Type checking
    - Name resolution
    """

    def __init__(self):
        self.global_scope = Scope("global")
        self.current_scope = self.global_scope
        self.errors: List[SemanticError] = []
        self.current_proc: Optional[ProcDef] = None

        # Initialize built-in types
        self._init_builtins()

    def _init_builtins(self):
        """Initialize built-in types and procedures"""
        # Built-in types
        self.global_scope.define(Symbol("INT", "type", INT_TYPE))
        self.global_scope.define(Symbol("BOOL", "type", BOOL_TYPE))
        self.global_scope.define(Symbol("CHAR", "type", CHAR_TYPE))
        self.global_scope.define(Symbol("DURATION", "type", DURATION_TYPE))
        self.global_scope.define(Symbol("TIME", "type", TIME_TYPE))
        self.global_scope.define(Symbol("EVENT", "type", EVENT_TYPE))

        # Built-in constants
        self.global_scope.define(Symbol("TRUE", "constant", BOOL_TYPE))
        self.global_scope.define(Symbol("FALSE", "constant", BOOL_TYPE))
        self.global_scope.define(Symbol("NULL", "constant", RefType()))

        # Built-in procedures (partial list)
        self.global_scope.define(Symbol("ABS", "proc",
            ProcType(params=[ParamInfo("x", INT_TYPE)], returns=INT_TYPE)))
        self.global_scope.define(Symbol("LENGTH", "proc",
            ProcType(params=[ParamInfo("s", CharsType())], returns=INT_TYPE)))
        self.global_scope.define(Symbol("SIZE", "proc",
            ProcType(params=[ParamInfo("x", ERROR_TYPE)], returns=INT_TYPE)))
        self.global_scope.define(Symbol("LOWER", "proc",
            ProcType(params=[ParamInfo("x", ERROR_TYPE)], returns=INT_TYPE)))
        self.global_scope.define(Symbol("UPPER", "proc",
            ProcType(params=[ParamInfo("x", ERROR_TYPE)], returns=INT_TYPE)))

    def analyze(self, program: Program) -> List[SemanticError]:
        """Analyze a complete program"""
        self.errors = []

        # First pass: collect all type definitions
        for module in program.modules:
            self._collect_types(module)

        # Second pass: analyze declarations and statements
        for module in program.modules:
            self._analyze_module(module)

        return self.errors

    def _error(self, message: str, location: Optional[SourceLocation] = None):
        """Record an error"""
        err = SemanticError(message, location)
        self.errors.append(err)

    def _collect_types(self, module: ModuleDef):
        """First pass: collect type definitions"""
        scope = self.current_scope.enter_scope(module.name)
        prev_scope = self.current_scope
        self.current_scope = scope

        for decl in module.declarations:
            if isinstance(decl, NewmodeNode):
                resolved = self._resolve_mode(decl.mode)
                sym = Symbol(decl.name, "type", resolved, decl.location)
                if not self.current_scope.define(sym):
                    self._error(f"Type '{decl.name}' already defined", decl.location)
            elif isinstance(decl, SynmodeNode):
                resolved = self._resolve_mode(decl.mode)
                sym = Symbol(decl.name, "type", resolved, decl.location)
                if not self.current_scope.define(sym):
                    self._error(f"Type alias '{decl.name}' already defined", decl.location)

        self.current_scope = prev_scope

    def _analyze_module(self, module: ModuleDef):
        """Analyze a module"""
        # Find the scope created in first pass
        found_scope = None
        for child in self.current_scope.children:
            if child.name.upper() == module.name.upper():
                found_scope = child
                break
        if found_scope:
            self.current_scope = found_scope
        else:
            self.current_scope = self.current_scope.enter_scope(module.name)

        # Analyze declarations
        for decl in module.declarations:
            self._analyze_declaration(decl)

        # Analyze procedures
        for proc in module.procs:
            self._analyze_proc(proc)

        # Analyze processes
        for process in module.processes:
            self._analyze_process(process)

        self.current_scope = self.current_scope.parent or self.global_scope

    def _analyze_declaration(self, decl: ASTNode):
        """Analyze a declaration"""
        if isinstance(decl, DclNode):
            resolved = self._resolve_mode(decl.mode)
            for name in decl.names:
                sym = Symbol(name, "variable", resolved, decl.location,
                           is_static=decl.static, is_readonly=decl.read_only)
                if not self.current_scope.define(sym):
                    self._error(f"Variable '{name}' already defined", decl.location)

            # Check initializer
            if decl.init:
                init_type = self._analyze_expression(decl.init)
                if not self._types_compatible(resolved, init_type):
                    self._error(f"Initializer type mismatch", decl.location)

        elif isinstance(decl, SynNode):
            value_type = self._analyze_expression(decl.value)
            if decl.mode:
                resolved = self._resolve_mode(decl.mode)
                if not self._types_compatible(resolved, value_type):
                    self._error(f"Constant type mismatch", decl.location)
            else:
                resolved = value_type
            sym = Symbol(decl.name, "constant", resolved, decl.location)
            if not self.current_scope.define(sym):
                self._error(f"Constant '{decl.name}' already defined", decl.location)

        elif isinstance(decl, SignalNode):
            params = []
            for param in decl.parameters:
                param_type = self._resolve_mode(param.mode)
                params.append(ParamInfo(param.name, param_type, param.param_mode))

            sig_type = ProcType(params=params, returns=None)
            sym = Symbol(decl.name, "signal", sig_type, decl.location)
            if not self.current_scope.define(sym):
                self._error(f"Signal '{decl.name}' already defined", decl.location)

    def _analyze_proc(self, proc: ProcDef):
        """Analyze a procedure definition"""
        # Create procedure type
        params = []
        for param in proc.parameters:
            param_type = self._resolve_mode(param.mode)
            params.append(ParamInfo(param.name, param_type, param.param_mode))

        returns = self._resolve_mode(proc.returns) if proc.returns else None
        proc_type = ProcType(params=params, returns=returns)

        # Define procedure in current scope
        sym = Symbol(proc.name, "proc", proc_type, proc.location)
        if not self.current_scope.define(sym):
            self._error(f"Procedure '{proc.name}' already defined", proc.location)

        # Enter procedure scope
        self.current_scope = self.current_scope.enter_scope(proc.name)
        self.current_proc = proc

        # Define parameters
        for param in proc.parameters:
            param_type = self._resolve_mode(param.mode)
            param_sym = Symbol(param.name, "variable", param_type, param.location)
            self.current_scope.define(param_sym)

        # Analyze declarations
        for decl in proc.declarations:
            self._analyze_declaration(decl)

        # Analyze statements
        for stmt in proc.statements:
            self._analyze_statement(stmt)

        # Exit procedure scope
        self.current_proc = None
        self.current_scope = self.current_scope.parent or self.global_scope

    def _analyze_process(self, process: ProcessDef):
        """Analyze a process definition"""
        params = []
        for param in process.parameters:
            param_type = self._resolve_mode(param.mode)
            params.append(ParamInfo(param.name, param_type, param.param_mode))

        proc_type = ProcType(params=params, returns=None)
        sym = Symbol(process.name, "process", proc_type, process.location)
        if not self.current_scope.define(sym):
            self._error(f"Process '{process.name}' already defined", process.location)

        # Enter process scope
        self.current_scope = self.current_scope.enter_scope(process.name)

        # Define parameters
        for param in process.parameters:
            param_type = self._resolve_mode(param.mode)
            param_sym = Symbol(param.name, "variable", param_type, param.location)
            self.current_scope.define(param_sym)

        # Analyze body
        for decl in process.declarations:
            self._analyze_declaration(decl)
        for stmt in process.statements:
            self._analyze_statement(stmt)

        self.current_scope = self.current_scope.parent or self.global_scope

    def _resolve_mode(self, mode: ModeNode) -> Type:
        """Resolve a mode node to a type"""
        if mode is None:
            return VOID_TYPE

        if isinstance(mode, IntMode):
            return INT_TYPE
        elif isinstance(mode, BoolMode):
            return BOOL_TYPE
        elif isinstance(mode, CharMode):
            return CHAR_TYPE
        elif isinstance(mode, CharsMode):
            # Try to evaluate length
            length = self._eval_const_expr(mode.length)
            return CharsType(length=length or 0, varying=mode.varying)
        elif isinstance(mode, BoolsMode):
            length = self._eval_const_expr(mode.length)
            return BoolsType(length=length or 0)
        elif isinstance(mode, SetMode):
            return SetType(elements=mode.elements)
        elif isinstance(mode, RangeMode):
            lower = self._eval_const_expr(mode.lower)
            upper = self._eval_const_expr(mode.upper)
            return RangeType(lower=lower or 0, upper=upper or 0)
        elif isinstance(mode, PowersetMode):
            base = self._resolve_mode(mode.base_mode)
            return Type(kind=TypeKind.POWERSET)
        elif isinstance(mode, RefMode):
            target = self._resolve_mode(mode.target_mode)
            return RefType(target=target, free=mode.free)
        elif isinstance(mode, StructMode):
            fields = []
            for fld in mode.fields:
                fld_type = self._resolve_mode(fld.mode)
                for name in fld.names:
                    fields.append(StructField(name, fld_type))
            return StructType(fields=fields)
        elif isinstance(mode, ArrayMode):
            idx = self._resolve_mode(mode.index_mode)
            elem = self._resolve_mode(mode.element_mode)
            return ArrayType(index_type=idx, element_type=elem)
        elif isinstance(mode, ProcMode):
            params = []
            for param in mode.parameters:
                param_type = self._resolve_mode(param.mode)
                params.append(ParamInfo(param.name, param_type, param.param_mode))
            ret = self._resolve_mode(mode.returns) if mode.returns else None
            return ProcType(params=params, returns=ret)
        elif isinstance(mode, BufferMode):
            size = self._eval_const_expr(mode.size)
            elem = self._resolve_mode(mode.element_mode)
            return BufferType(size=size or 0, element_type=elem)
        elif isinstance(mode, EventMode):
            return EVENT_TYPE
        elif isinstance(mode, DurationMode):
            return DURATION_TYPE
        elif isinstance(mode, TimeMode):
            return TIME_TYPE
        elif isinstance(mode, NamedMode):
            sym = self.current_scope.lookup(mode.name)
            if sym and sym.kind == "type":
                return sym.type
            self._error(f"Unknown type '{mode.name}'", mode.location)
            return ERROR_TYPE
        else:
            return ERROR_TYPE

    def _eval_const_expr(self, expr: Expression) -> Optional[int]:
        """Try to evaluate a constant expression"""
        if isinstance(expr, Literal):
            if expr.kind == 'int':
                return expr.value
        elif isinstance(expr, Identifier):
            sym = self.current_scope.lookup(expr.name)
            if sym and sym.kind == "constant":
                pass  # Would need stored value
        elif isinstance(expr, BinaryOp):
            left = self._eval_const_expr(expr.left)
            right = self._eval_const_expr(expr.right)
            if left is not None and right is not None:
                if expr.op == '+':
                    return left + right
                elif expr.op == '-':
                    return left - right
                elif expr.op == '*':
                    return left * right
                elif expr.op == '/':
                    return left // right if right != 0 else None
        return None

    def _analyze_statement(self, stmt: Statement):
        """Analyze a statement"""
        if isinstance(stmt, AssignStmt):
            value_type = self._analyze_expression(stmt.value)
            for target in stmt.targets:
                target_type = self._analyze_expression(target)
                if not self._types_compatible(target_type, value_type):
                    self._error(f"Assignment type mismatch", stmt.location)
                # Check if target is assignable (not readonly)
                if isinstance(target, Identifier):
                    sym = self.current_scope.lookup(target.name)
                    if sym and sym.is_readonly:
                        self._error(f"Cannot assign to readonly variable '{target.name}'",
                                  stmt.location)

        elif isinstance(stmt, IfStmt):
            cond_type = self._analyze_expression(stmt.condition)
            if cond_type.kind != TypeKind.BOOL:
                self._error("IF condition must be boolean", stmt.location)
            for s in stmt.then_stmts:
                self._analyze_statement(s)
            for elsif in stmt.elsif_parts:
                cond_type = self._analyze_expression(elsif.condition)
                if cond_type.kind != TypeKind.BOOL:
                    self._error("ELSIF condition must be boolean", elsif.location)
                for s in elsif.statements:
                    self._analyze_statement(s)
            for s in stmt.else_stmts:
                self._analyze_statement(s)

        elif isinstance(stmt, CaseStmt):
            selector_type = self._analyze_expression(stmt.selector)
            for alt in stmt.alternatives:
                for val in alt.values:
                    val_type = self._analyze_expression(val)
                    if not self._types_compatible(selector_type, val_type):
                        self._error("CASE value type mismatch", val.location)
                for s in alt.statements:
                    self._analyze_statement(s)
            for s in stmt.else_stmts:
                self._analyze_statement(s)

        elif isinstance(stmt, DoWhileStmt):
            cond_type = self._analyze_expression(stmt.condition)
            if cond_type.kind != TypeKind.BOOL:
                self._error("WHILE condition must be boolean", stmt.location)
            for s in stmt.statements:
                self._analyze_statement(s)

        elif isinstance(stmt, DoForStmt):
            # Enter loop scope for loop variable
            self.current_scope = self.current_scope.enter_scope("for_loop")
            loop_var_sym = Symbol(stmt.var, "variable", INT_TYPE, stmt.location)
            self.current_scope.define(loop_var_sym)

            start_type = self._analyze_expression(stmt.start)
            end_type = self._analyze_expression(stmt.end)
            if stmt.step:
                step_type = self._analyze_expression(stmt.step)

            for s in stmt.statements:
                self._analyze_statement(s)

            self.current_scope = self.current_scope.parent or self.global_scope

        elif isinstance(stmt, DoEverStmt):
            for s in stmt.statements:
                self._analyze_statement(s)

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                ret_type = self._analyze_expression(stmt.value)
                if self.current_proc and self.current_proc.returns:
                    expected = self._resolve_mode(self.current_proc.returns)
                    if not self._types_compatible(expected, ret_type):
                        self._error("RETURN type mismatch", stmt.location)

        elif isinstance(stmt, CallStmt):
            self._analyze_expression(ProcCall(proc=stmt.proc, arguments=stmt.arguments))

        elif isinstance(stmt, StartStmt):
            sym = self.current_scope.lookup(stmt.process)
            if not sym or sym.kind != "process":
                self._error(f"Unknown process '{stmt.process}'", stmt.location)
            else:
                # Check argument count/types
                if isinstance(sym.type, ProcType):
                    if len(stmt.arguments) != len(sym.type.params):
                        self._error(f"Wrong number of arguments for process '{stmt.process}'",
                                  stmt.location)
                    for arg, param in zip(stmt.arguments, sym.type.params):
                        arg_type = self._analyze_expression(arg)
                        if not self._types_compatible(param.type, arg_type):
                            self._error(f"Argument type mismatch for '{param.name}'",
                                      arg.location)

        elif isinstance(stmt, SendStmt):
            sym = self.current_scope.lookup(stmt.signal)
            if not sym or sym.kind != "signal":
                self._error(f"Unknown signal '{stmt.signal}'", stmt.location)

        elif isinstance(stmt, ReceiveCaseStmt):
            for alt in stmt.alternatives:
                sym = self.current_scope.lookup(alt.signal)
                if not sym or sym.kind != "signal":
                    self._error(f"Unknown signal '{alt.signal}'", stmt.location)
                for s in alt.statements:
                    self._analyze_statement(s)

        elif isinstance(stmt, AssertStmt):
            cond_type = self._analyze_expression(stmt.condition)
            if cond_type.kind != TypeKind.BOOL:
                self._error("ASSERT condition must be boolean", stmt.location)

        elif isinstance(stmt, BeginEndBlock):
            self.current_scope = self.current_scope.enter_scope("block")
            for d in stmt.declarations:
                self._analyze_declaration(d)
            for s in stmt.statements:
                self._analyze_statement(s)
            self.current_scope = self.current_scope.parent or self.global_scope

    def _analyze_expression(self, expr: Expression) -> Type:
        """Analyze an expression and return its type"""
        if isinstance(expr, Literal):
            if expr.kind == 'int':
                return INT_TYPE
            elif expr.kind == 'bool':
                return BOOL_TYPE
            elif expr.kind == 'char':
                return CHAR_TYPE
            elif expr.kind == 'string':
                return CharsType(length=len(expr.value))
            elif expr.kind == 'null':
                return RefType()
            elif expr.kind == 'float':
                return INT_TYPE  # Treat as int for now
            else:
                return ERROR_TYPE

        elif isinstance(expr, Identifier):
            sym = self.current_scope.lookup(expr.name)
            if not sym:
                self._error(f"Undefined identifier '{expr.name}'", expr.location)
                return ERROR_TYPE
            return sym.type

        elif isinstance(expr, BinaryOp):
            left_type = self._analyze_expression(expr.left)
            right_type = self._analyze_expression(expr.right)

            # Arithmetic operators
            if expr.op in ('+', '-', '*', '/', 'MOD', 'REM', '**'):
                if left_type.kind == TypeKind.INT and right_type.kind == TypeKind.INT:
                    return INT_TYPE
                elif expr.op == '//' and left_type.kind == TypeKind.CHARS:
                    return left_type  # String concatenation
                else:
                    self._error(f"Invalid operand types for '{expr.op}'", expr.location)
                    return ERROR_TYPE

            # Comparison operators
            elif expr.op in ('=', '/=', '<', '>', '<=', '>='):
                if self._types_compatible(left_type, right_type):
                    return BOOL_TYPE
                else:
                    self._error(f"Cannot compare different types", expr.location)
                    return BOOL_TYPE

            # Logical operators
            elif expr.op in ('AND', 'OR', 'XOR'):
                if left_type.kind == TypeKind.BOOL and right_type.kind == TypeKind.BOOL:
                    return BOOL_TYPE
                else:
                    self._error(f"Logical operators require boolean operands", expr.location)
                    return BOOL_TYPE

            # String concatenation
            elif expr.op == '//':
                if left_type.kind == TypeKind.CHARS and right_type.kind == TypeKind.CHARS:
                    # Result length is sum of operand lengths
                    len1 = left_type.length if isinstance(left_type, CharsType) else 0
                    len2 = right_type.length if isinstance(right_type, CharsType) else 0
                    return CharsType(length=len1 + len2)
                else:
                    self._error("Concatenation requires string operands", expr.location)
                    return ERROR_TYPE

            # IN operator
            elif expr.op == 'IN':
                return BOOL_TYPE

            return ERROR_TYPE

        elif isinstance(expr, UnaryOp):
            operand_type = self._analyze_expression(expr.operand)
            if expr.op == 'NOT':
                if operand_type.kind == TypeKind.BOOL:
                    return BOOL_TYPE
                else:
                    self._error("NOT requires boolean operand", expr.location)
                    return BOOL_TYPE
            elif expr.op in ('-', '+'):
                if operand_type.kind == TypeKind.INT:
                    return INT_TYPE
                else:
                    self._error(f"'{expr.op}' requires integer operand", expr.location)
                    return INT_TYPE
            return ERROR_TYPE

        elif isinstance(expr, ArrayAccess):
            array_type = self._analyze_expression(expr.array)
            index_type = self._analyze_expression(expr.index)

            if isinstance(array_type, ArrayType):
                return array_type.element_type
            elif isinstance(array_type, CharsType):
                return CHAR_TYPE
            else:
                self._error("Cannot index non-array type", expr.location)
                return ERROR_TYPE

        elif isinstance(expr, FieldAccess):
            struct_type = self._analyze_expression(expr.struct)
            if isinstance(struct_type, StructType):
                for fld in struct_type.fields:
                    if fld.name.upper() == expr.field.upper():
                        return fld.type
                self._error(f"Unknown field '{expr.field}'", expr.location)
            else:
                self._error("Cannot access field of non-struct type", expr.location)
            return ERROR_TYPE

        elif isinstance(expr, DerefAccess):
            ref_type = self._analyze_expression(expr.ref)
            if isinstance(ref_type, RefType) and ref_type.target:
                return ref_type.target
            else:
                self._error("Cannot dereference non-reference type", expr.location)
                return ERROR_TYPE

        elif isinstance(expr, ProcCall):
            proc_type = self._analyze_expression(expr.proc)
            if isinstance(proc_type, ProcType):
                # It's a procedure call
                # Check argument count
                if len(expr.arguments) != len(proc_type.params):
                    self._error(f"Wrong number of arguments", expr.location)
                else:
                    # Check argument types
                    for arg, param in zip(expr.arguments, proc_type.params):
                        arg_type = self._analyze_expression(arg)
                        if not self._types_compatible(param.type, arg_type):
                            self._error(f"Argument type mismatch", arg.location)
                return proc_type.returns or VOID_TYPE
            elif isinstance(proc_type, ArrayType):
                # It's array access, not a call
                if len(expr.arguments) == 1:
                    self._analyze_expression(expr.arguments[0])
                    return proc_type.element_type
                else:
                    self._error("Array requires single index", expr.location)
                    return ERROR_TYPE
            elif isinstance(proc_type, CharsType):
                # String indexing
                if len(expr.arguments) == 1:
                    self._analyze_expression(expr.arguments[0])
                    return CHAR_TYPE
                else:
                    return ERROR_TYPE
            else:
                # Unknown - could be error or builtin
                for arg in expr.arguments:
                    self._analyze_expression(arg)
                return ERROR_TYPE

        elif isinstance(expr, IfExpr):
            cond_type = self._analyze_expression(expr.condition)
            if cond_type.kind != TypeKind.BOOL:
                self._error("IF expression condition must be boolean", expr.location)
            then_type = self._analyze_expression(expr.then_expr)
            else_type = self._analyze_expression(expr.else_expr)
            if not self._types_compatible(then_type, else_type):
                self._error("IF expression branches have different types", expr.location)
            return then_type

        elif isinstance(expr, BuiltinCall):
            # Analyze arguments
            arg_types = [self._analyze_expression(arg) for arg in expr.arguments]
            sym = self.current_scope.lookup(expr.name)
            if sym and isinstance(sym.type, ProcType):
                return sym.type.returns or VOID_TYPE
            # Default return types for builtins
            if expr.name.upper() in ('ABS', 'LENGTH', 'SIZE', 'LOWER', 'UPPER', 'NUM'):
                return INT_TYPE
            elif expr.name.upper() == 'CHAR':
                return CHAR_TYPE
            return ERROR_TYPE

        return ERROR_TYPE

    def _types_compatible(self, expected: Type, actual: Type) -> bool:
        """Check if types are compatible for assignment/comparison"""
        if expected is None or actual is None:
            return True

        if expected.kind == TypeKind.ERROR or actual.kind == TypeKind.ERROR:
            return True  # Don't cascade errors

        # Same kind is generally compatible
        if expected.kind == actual.kind:
            return True

        # INT and RANGE are compatible
        if expected.kind in (TypeKind.INT, TypeKind.RANGE):
            if actual.kind in (TypeKind.INT, TypeKind.RANGE):
                return True

        # NULL is compatible with REF
        if expected.kind == TypeKind.REF and actual.kind == TypeKind.REF:
            return True

        # CHAR and CHARS are related
        if expected.kind == TypeKind.CHAR and actual.kind == TypeKind.CHAR:
            return True
        if expected.kind == TypeKind.CHARS and actual.kind == TypeKind.CHARS:
            return True
        # String literal (CHARS) can be assigned to CHARS of sufficient size
        if expected.kind == TypeKind.CHARS:
            if actual.kind == TypeKind.CHARS:
                return True
        # Single-character string is compatible with CHAR
        if expected.kind == TypeKind.CHAR and actual.kind == TypeKind.CHARS:
            if isinstance(actual, CharsType) and actual.length == 1:
                return True
            # Be lenient - any short string can be assigned to CHAR
            return True
        # CHAR can be assigned to CHARS
        if expected.kind == TypeKind.CHARS and actual.kind == TypeKind.CHAR:
            return True

        # SET elements are compatible with INT for comparisons
        if expected.kind == TypeKind.SET and actual.kind == TypeKind.SET:
            return True

        return False


def analyze(program: Program) -> List[SemanticError]:
    """Convenience function to analyze a CHILL program"""
    analyzer = SemanticAnalyzer()
    return analyzer.analyze(program)

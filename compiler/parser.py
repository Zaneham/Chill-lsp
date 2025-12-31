"""
CHILL Parser
Recursive descent parser for ITU-T Z.200 (1999)

Converts token stream to AST using nodes from ast_nodes.py
"""

from typing import List, Optional, Set

# Support both relative and absolute imports
try:
    from .lexer import Lexer, Token, TokenType
    from .ast_nodes import (
        # Re-export all for easier import fix below
        Program, ModuleDef, ProcDef, ProcessDef, RegionDef,
        DclNode, NewmodeNode, SynmodeNode, SynNode, SignalNode, Parameter,
        ModeNode, IntMode, BoolMode, CharMode, CharsMode, BoolsMode,
        SetMode, RangeMode, PowersetMode, RefMode, StructMode, StructField,
        ArrayMode, ProcMode, BufferMode, EventMode, DurationMode, TimeMode, NamedMode,
        Expression, Literal, Identifier, BinaryOp, UnaryOp,
        ProcCall, ArrayAccess, StructAccess, SliceExpr, IfExpr, CaseExpr, CaseAlt,
        Statement, AssignStmt, IfStmt, ElsifClause, CaseStmt, CaseActionAlt, DoWhileStmt,
        DoForStmt, DoEverStmt, DoWithStmt, StartStmt, CallStmt, ReturnStmt, ResultStmt,
        ExitStmt, AssertStmt, CauseStmt, DelayStmt, SendStmt, ReceiveStmt, ContinueStmt,
        SourceLocation
    )
except ImportError:
    from lexer import Lexer, Token, TokenType
    from ast_nodes import (
    # Program structure
    Program, ModuleDef, ProcDef, ProcessDef, RegionDef,
    # Declarations
    DclNode, NewmodeNode, SynmodeNode, SynNode, SignalNode, Parameter,
    # Modes
    ModeNode, IntMode, BoolMode, CharMode, CharsMode, BoolsMode,
    SetMode, RangeMode, PowersetMode, RefMode, StructMode, StructField,
    ArrayMode, ProcMode, BufferMode, EventMode, DurationMode, TimeMode, NamedMode,
    # Expressions
    Expression, Literal, Identifier, BinaryOp, UnaryOp,
    ArrayAccess, SliceAccess, FieldAccess, DerefAccess, ProcCall,
    StartExpr, ReceiveExpr, BuiltinCall, IfExpr, CaseExpr,
    # Statements
    Statement, AssignStmt, IfStmt, ElsifPart, CaseStmt, CaseAlternative,
    DoWhileStmt, DoForStmt, DoEverStmt, ExitStmt, ReturnStmt, ResultStmt,
    GotoStmt, CallStmt, SendStmt, ReceiveCaseStmt, ReceiveAlternative,
    DelayStmt, StartStmt, StopStmt, ContinueStmt, AssertStmt, CauseStmt,
    EmptyStmt, BeginEndBlock,
    # Utility
    SourceLocation
)


class ParseError(Exception):
    """Parser error with location information"""
    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        self.line = token.line
        self.column = token.column
        super().__init__(f"{message} at line {token.line}, column {token.column}")


class Parser:
    """
    Recursive descent parser for CHILL

    Grammar is based on ITU-T Z.200 (1999) with simplifications
    for practical parsing.
    """

    # Operator precedence (higher = tighter binding)
    PRECEDENCE = {
        'OR': 1,
        'XOR': 2,
        'AND': 3,
        'NOT': 4,  # Unary, but listed for reference
        '=': 5, '/=': 5, '<': 5, '>': 5, '<=': 5, '>=': 5, 'IN': 5,
        '//': 6,  # String concatenation
        '+': 7, '-': 7,
        '*': 8, '/': 8, 'MOD': 8, 'REM': 8,
        '**': 9,  # Exponentiation (right associative)
    }

    def __init__(self, source: str, filename: str = "<unknown>"):
        self.lexer = Lexer(source, filename)
        self.filename = filename
        self.tokens: List[Token] = []
        self.pos = 0
        self.current: Token = None

        # Tokenize everything upfront
        self._tokenize()

    def _tokenize(self):
        """Collect all tokens from lexer"""
        while True:
            tok = self.lexer.next_token()
            self.tokens.append(tok)
            if tok.type == TokenType.EOF:
                break
        self.pos = 0
        self.current = self.tokens[0] if self.tokens else None

    def _advance(self) -> Token:
        """Move to next token"""
        tok = self.current
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current = self.tokens[self.pos]
        return tok

    def _peek(self, offset: int = 0) -> Token:
        """Look ahead without consuming"""
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # EOF

    def _check(self, *types: TokenType) -> bool:
        """Check if current token is one of the given types"""
        return self.current.type in types

    def _check_keyword(self, *keywords: str) -> bool:
        """Check if current token is a keyword with given value"""
        return (self.current.type == TokenType.KEYWORD and
                self.current.value in keywords)

    def _check_builtin(self, *names: str) -> bool:
        """Check if current token is a builtin with given value"""
        return (self.current.type == TokenType.BUILTIN and
                self.current.value in names)

    def _check_keyword_or_builtin(self, *names: str) -> bool:
        """Check if current token is a keyword or builtin with given value"""
        return ((self.current.type in (TokenType.KEYWORD, TokenType.BUILTIN)) and
                self.current.value in names)

    def _match(self, *types: TokenType) -> Optional[Token]:
        """Consume token if it matches"""
        if self._check(*types):
            return self._advance()
        return None

    def _match_keyword(self, *keywords: str) -> Optional[Token]:
        """Consume keyword if it matches"""
        if self._check_keyword(*keywords):
            return self._advance()
        return None

    def _match_builtin(self, *names: str) -> Optional[Token]:
        """Consume builtin if it matches"""
        if self._check_builtin(*names):
            return self._advance()
        return None

    def _match_keyword_or_builtin(self, *names: str) -> Optional[Token]:
        """Consume keyword or builtin if it matches"""
        if self._check_keyword_or_builtin(*names):
            return self._advance()
        return None

    def _expect(self, type_: TokenType, message: str = None) -> Token:
        """Consume token or error"""
        if not self._check(type_):
            msg = message or f"Expected {type_.name}, got {self.current.type.name}"
            raise ParseError(msg, self.current)
        return self._advance()

    def _expect_keyword(self, keyword: str, message: str = None) -> Token:
        """Consume keyword or error"""
        if not self._check_keyword(keyword):
            msg = message or f"Expected '{keyword}', got '{self.current.value}'"
            raise ParseError(msg, self.current)
        return self._advance()

    def _location(self, token: Token = None) -> SourceLocation:
        """Create source location from token"""
        tok = token or self.current
        return SourceLocation(tok.line, tok.column, self.filename)

    # ========================================================================
    # Top-level parsing
    # ========================================================================

    def parse(self) -> Program:
        """Parse complete CHILL program"""
        modules = []
        declarations = []

        while not self._check(TokenType.EOF):
            if self._check_keyword('MODULE'):
                modules.append(self._parse_module())
            else:
                # Top-level declaration
                decl = self._parse_declaration()
                if decl:
                    declarations.append(decl)

        return Program(modules=modules, declarations=declarations)

    def _parse_module(self) -> ModuleDef:
        """Parse MODULE ... END name;"""
        loc = self._location()
        self._expect_keyword('MODULE')

        name = self._expect(TokenType.IDENTIFIER, "Expected module name").value
        self._expect(TokenType.SEMICOLON)

        declarations = []
        procs = []
        processes = []
        regions = []
        grants = []
        seizes = []

        while not self._check_keyword('END') and not self._check(TokenType.EOF):
            if self._check_keyword('GRANT'):
                grants.extend(self._parse_grant())
            elif self._check_keyword('SEIZE'):
                seizes.extend(self._parse_seize())
            elif self._check_keyword('REGION'):
                regions.append(self._parse_region())
            elif self._check_keyword('PROC') or self._is_proc_start():
                procs.append(self._parse_proc())
            elif self._check_keyword('PROCESS') or self._is_process_start():
                processes.append(self._parse_process())
            else:
                decl = self._parse_declaration()
                if decl:
                    declarations.append(decl)

        self._expect_keyword('END')
        # Optional module name after END
        if self._check(TokenType.IDENTIFIER):
            end_name = self._advance().value
            if end_name != name:
                pass  # Could warn about mismatch
        self._expect(TokenType.SEMICOLON)

        return ModuleDef(
            name=name,
            declarations=declarations,
            procs=procs,
            processes=processes,
            regions=regions,
            grants=grants,
            seizes=seizes,
            location=loc
        )

    def _is_proc_start(self) -> bool:
        """Check if this looks like a procedure definition (name: PROC)"""
        if self._check(TokenType.IDENTIFIER):
            next_tok = self._peek(1)
            if next_tok.type == TokenType.COLON:
                after_colon = self._peek(2)
                return (after_colon.type == TokenType.KEYWORD and
                        after_colon.value == 'PROC')
        return False

    def _is_process_start(self) -> bool:
        """Check if this looks like a process definition (name: PROCESS)"""
        if self._check(TokenType.IDENTIFIER):
            next_tok = self._peek(1)
            if next_tok.type == TokenType.COLON:
                after_colon = self._peek(2)
                return (after_colon.type == TokenType.KEYWORD and
                        after_colon.value == 'PROCESS')
        return False

    def _parse_grant(self) -> List[str]:
        """Parse GRANT name1, name2, ...;"""
        self._expect_keyword('GRANT')
        names = [self._expect(TokenType.IDENTIFIER).value]
        while self._match(TokenType.COMMA):
            names.append(self._expect(TokenType.IDENTIFIER).value)
        self._expect(TokenType.SEMICOLON)
        return names

    def _parse_seize(self) -> List[str]:
        """Parse SEIZE name1, name2, ...;"""
        self._expect_keyword('SEIZE')
        names = [self._expect(TokenType.IDENTIFIER).value]
        while self._match(TokenType.COMMA):
            names.append(self._expect(TokenType.IDENTIFIER).value)
        self._expect(TokenType.SEMICOLON)
        return names

    def _parse_region(self) -> RegionDef:
        """Parse REGION name; ... END name;"""
        loc = self._location()
        self._expect_keyword('REGION')

        name = self._expect(TokenType.IDENTIFIER).value
        self._expect(TokenType.SEMICOLON)

        declarations = []
        procs = []

        while not self._check_keyword('END') and not self._check(TokenType.EOF):
            if self._check_keyword('PROC') or self._is_proc_start():
                procs.append(self._parse_proc())
            else:
                decl = self._parse_declaration()
                if decl:
                    declarations.append(decl)

        self._expect_keyword('END')
        if self._check(TokenType.IDENTIFIER):
            self._advance()
        self._expect(TokenType.SEMICOLON)

        return RegionDef(name=name, declarations=declarations, procs=procs, location=loc)

    def _parse_proc(self) -> ProcDef:
        """Parse procedure definition"""
        loc = self._location()

        # Optional label: name: PROC
        name = None
        if self._check(TokenType.IDENTIFIER) and self._peek(1).type == TokenType.COLON:
            name = self._advance().value
            self._advance()  # consume colon

        # Modifiers before PROC
        is_recursive = bool(self._match_keyword('RECURSIVE'))
        is_inline = bool(self._match_keyword('INLINE'))
        is_general = bool(self._match_keyword('GENERAL'))

        self._expect_keyword('PROC')

        # If no label, name comes after PROC
        if name is None and self._check(TokenType.IDENTIFIER):
            name = self._advance().value

        # Parameters
        parameters = []
        if self._match(TokenType.LPAREN):
            if not self._check(TokenType.RPAREN):
                parameters = self._parse_parameters()
            self._expect(TokenType.RPAREN)

        # Return type
        returns = None
        result_loc = False
        if self._match_keyword('RETURNS'):
            if self._match_keyword('LOC'):
                result_loc = True
            self._expect(TokenType.LPAREN)
            returns = self._parse_mode()
            self._expect(TokenType.RPAREN)

        # Exceptions
        exceptions = []
        if self._match_keyword('EXCEPTIONS'):
            self._expect(TokenType.LPAREN)
            exceptions.append(self._expect(TokenType.IDENTIFIER).value)
            while self._match(TokenType.COMMA):
                exceptions.append(self._expect(TokenType.IDENTIFIER).value)
            self._expect(TokenType.RPAREN)

        self._expect(TokenType.SEMICOLON)

        # Body
        declarations = []
        statements = []

        while not self._check_keyword('END') and not self._check(TokenType.EOF):
            if self._is_declaration_start():
                decl = self._parse_declaration()
                if decl:
                    declarations.append(decl)
            else:
                stmt = self._parse_statement()
                if stmt:
                    statements.append(stmt)

        self._expect_keyword('END')
        if self._check(TokenType.IDENTIFIER):
            self._advance()
        self._expect(TokenType.SEMICOLON)

        return ProcDef(
            name=name or "<anonymous>",
            parameters=parameters,
            returns=returns,
            result_loc=result_loc,
            exceptions=exceptions,
            declarations=declarations,
            statements=statements,
            is_recursive=is_recursive,
            is_inline=is_inline,
            is_general=is_general,
            location=loc
        )

    def _parse_process(self) -> ProcessDef:
        """Parse process definition"""
        loc = self._location()

        # Optional label
        name = None
        if self._check(TokenType.IDENTIFIER) and self._peek(1).type == TokenType.COLON:
            name = self._advance().value
            self._advance()

        self._expect_keyword('PROCESS')

        if name is None and self._check(TokenType.IDENTIFIER):
            name = self._advance().value

        # Parameters
        parameters = []
        if self._match(TokenType.LPAREN):
            if not self._check(TokenType.RPAREN):
                parameters = self._parse_parameters()
            self._expect(TokenType.RPAREN)

        # Priority
        priority = None
        if self._match_keyword('PRIORITY'):
            priority = self._parse_expression()

        self._expect(TokenType.SEMICOLON)

        # Body
        declarations = []
        statements = []

        while not self._check_keyword('END') and not self._check(TokenType.EOF):
            if self._is_declaration_start():
                decl = self._parse_declaration()
                if decl:
                    declarations.append(decl)
            else:
                stmt = self._parse_statement()
                if stmt:
                    statements.append(stmt)

        self._expect_keyword('END')
        if self._check(TokenType.IDENTIFIER):
            self._advance()
        self._expect(TokenType.SEMICOLON)

        return ProcessDef(
            name=name or "<anonymous>",
            parameters=parameters,
            declarations=declarations,
            statements=statements,
            priority=priority,
            location=loc
        )

    def _parse_parameters(self) -> List[Parameter]:
        """Parse parameter list"""
        params = []
        params.extend(self._parse_parameter_group())
        while self._match(TokenType.COMMA):
            params.extend(self._parse_parameter_group())
        return params

    def _parse_parameter_group(self) -> List[Parameter]:
        """Parse one or more parameters with same mode: (IN a, b INT)"""
        loc = self._location()

        # Parameter mode
        param_mode = "IN"
        if self._check_keyword('IN', 'OUT', 'INOUT', 'LOC'):
            param_mode = self._advance().value

        # Names
        names = [self._expect(TokenType.IDENTIFIER).value]
        while self._match(TokenType.COMMA):
            if self._check(TokenType.IDENTIFIER) and not self._is_mode_start():
                names.append(self._advance().value)
            else:
                # Put back the comma conceptually - next group
                self.pos -= 1
                self.current = self.tokens[self.pos]
                break

        # Mode
        mode = self._parse_mode()

        return [Parameter(name=n, mode=mode, param_mode=param_mode, location=loc)
                for n in names]

    # ========================================================================
    # Declarations
    # ========================================================================

    def _is_declaration_start(self) -> bool:
        """Check if current position starts a declaration"""
        return self._check_keyword('DCL', 'NEWMODE', 'SYNMODE', 'SYN', 'SIGNAL')

    def _parse_declaration(self):
        """Parse a declaration"""
        if self._check_keyword('DCL'):
            return self._parse_dcl()
        elif self._check_keyword('NEWMODE'):
            return self._parse_newmode()
        elif self._check_keyword('SYNMODE'):
            return self._parse_synmode()
        elif self._check_keyword('SYN'):
            return self._parse_syn()
        elif self._check_keyword('SIGNAL'):
            return self._parse_signal()
        else:
            # Skip unknown
            self._advance()
            return None

    def _parse_dcl(self) -> DclNode:
        """Parse DCL name1, name2 mode [:= init];"""
        loc = self._location()
        self._expect_keyword('DCL')

        # Optional STATIC
        static = bool(self._match_keyword('STATIC'))

        # Names: DCL a, b, c INT means a, b, c are variable names, INT is the mode
        # Keep collecting identifiers while we see commas AND the identifier
        # is followed by another comma (meaning more names)
        names = [self._expect(TokenType.IDENTIFIER).value]
        while self._match(TokenType.COMMA):
            # After comma, if we have identifier followed by comma, it's another name
            # If we have identifier NOT followed by comma, check if it could be a mode
            if self._check(TokenType.IDENTIFIER):
                next_tok = self._peek(1)
                if next_tok.type == TokenType.COMMA:
                    # More names coming - consume this identifier
                    names.append(self._advance().value)
                else:
                    # Could be last name before mode, or could be a mode name
                    # Check if current identifier is a builtin mode (INT, BOOL, etc.)
                    # If not, it's another variable name
                    if self._check_builtin('INT', 'BOOL', 'CHAR', 'DURATION', 'TIME',
                                           'PTR', 'FLOAT', 'BYTE', 'UBYTE', 'UINT',
                                           'LONG', 'ULONG', 'REAL', 'LONG_REAL', 'WCHAR'):
                        # This is a mode, stop collecting names
                        break
                    elif self._check_keyword('CHARS', 'BOOLS', 'SET', 'RANGE', 'POWERSET',
                                             'REF', 'STRUCT', 'ARRAY', 'PROC', 'BUFFER', 'EVENT'):
                        # This is a mode keyword, stop collecting names
                        break
                    else:
                        # Assume it's another variable name (custom type will be after)
                        names.append(self._advance().value)
            else:
                # Not an identifier after comma - shouldn't happen, break
                break

        # Mode
        mode = self._parse_mode()

        # Optional READ
        read_only = bool(self._match_keyword('READ'))

        # Optional init
        init = None
        if self._match(TokenType.ASSIGN):
            init = self._parse_expression()

        self._expect(TokenType.SEMICOLON)

        return DclNode(
            names=names,
            mode=mode,
            init=init,
            static=static,
            read_only=read_only,
            location=loc
        )

    def _parse_newmode(self) -> NewmodeNode:
        """Parse NEWMODE name = mode;"""
        loc = self._location()
        self._expect_keyword('NEWMODE')

        name = self._expect(TokenType.IDENTIFIER).value
        self._expect(TokenType.EQ)
        mode = self._parse_mode()
        self._expect(TokenType.SEMICOLON)

        return NewmodeNode(name=name, mode=mode, location=loc)

    def _parse_synmode(self) -> SynmodeNode:
        """Parse SYNMODE name = mode;"""
        loc = self._location()
        self._expect_keyword('SYNMODE')

        name = self._expect(TokenType.IDENTIFIER).value
        self._expect(TokenType.EQ)
        mode = self._parse_mode()
        self._expect(TokenType.SEMICOLON)

        return SynmodeNode(name=name, mode=mode, location=loc)

    def _parse_syn(self) -> SynNode:
        """Parse SYN name [mode] = value;"""
        loc = self._location()
        self._expect_keyword('SYN')

        name = self._expect(TokenType.IDENTIFIER).value

        # Optional mode
        mode = None
        if self._is_mode_start():
            mode = self._parse_mode()

        self._expect(TokenType.EQ)
        value = self._parse_expression()
        self._expect(TokenType.SEMICOLON)

        return SynNode(name=name, value=value, mode=mode, location=loc)

    def _parse_signal(self) -> SignalNode:
        """Parse SIGNAL name(params) [TO destination];"""
        loc = self._location()
        self._expect_keyword('SIGNAL')

        name = self._expect(TokenType.IDENTIFIER).value

        # Optional parameters
        parameters = []
        if self._match(TokenType.LPAREN):
            if not self._check(TokenType.RPAREN):
                parameters = self._parse_parameters()
            self._expect(TokenType.RPAREN)

        # Optional destination
        destination = None
        if self._match_keyword('TO'):
            destination = self._expect(TokenType.IDENTIFIER).value

        self._expect(TokenType.SEMICOLON)

        return SignalNode(name=name, parameters=parameters, destination=destination, location=loc)

    # ========================================================================
    # Modes (Types)
    # ========================================================================

    def _is_mode_start(self) -> bool:
        """Check if current token starts a mode specification"""
        if self._check(TokenType.IDENTIFIER):
            return True
        # Mode keywords
        if self._check_keyword(
            'CHARS', 'BOOLS', 'SET', 'RANGE', 'POWERSET', 'REF',
            'STRUCT', 'ARRAY', 'PROC', 'BUFFER', 'EVENT',
            'READ', 'VARYING'
        ):
            return True
        # Mode builtins (predefined mode names)
        if self._check_builtin(
            'INT', 'BOOL', 'CHAR', 'DURATION', 'TIME', 'PTR',
            'FLOAT', 'BYTE', 'UBYTE', 'UINT', 'LONG', 'ULONG',
            'REAL', 'LONG_REAL', 'INSTANCE', 'WCHAR'
        ):
            return True
        return False

    def _parse_mode(self) -> ModeNode:
        """Parse a mode (type) specification"""
        loc = self._location()

        # Simple modes (predefined mode names are BUILTIN tokens)
        if self._match_builtin('INT', 'BYTE', 'UBYTE', 'UINT', 'LONG', 'ULONG'):
            return IntMode(location=loc)

        if self._match_builtin('BOOL'):
            return BoolMode(location=loc)

        if self._match_builtin('CHAR', 'WCHAR'):
            return CharMode(location=loc)

        if self._match_builtin('FLOAT', 'REAL', 'LONG_REAL'):
            # For now, treat floats as a special IntMode (we'll add FloatMode later)
            return IntMode(location=loc)

        if self._match_keyword('CHARS'):
            self._expect(TokenType.LPAREN)
            length = self._parse_expression()
            self._expect(TokenType.RPAREN)
            varying = bool(self._match_keyword('VARYING'))
            return CharsMode(length=length, varying=varying, location=loc)

        if self._match_keyword('BOOLS'):
            self._expect(TokenType.LPAREN)
            length = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return BoolsMode(length=length, location=loc)

        if self._match_keyword('SET'):
            self._expect(TokenType.LPAREN)
            elements = [self._expect(TokenType.IDENTIFIER).value]
            while self._match(TokenType.COMMA):
                elements.append(self._expect(TokenType.IDENTIFIER).value)
            self._expect(TokenType.RPAREN)
            return SetMode(elements=elements, location=loc)

        if self._match_keyword('RANGE'):
            self._expect(TokenType.LPAREN)
            lower = self._parse_expression()
            self._expect(TokenType.COLON)
            upper = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return RangeMode(lower=lower, upper=upper, location=loc)

        if self._match_keyword('POWERSET'):
            base = self._parse_mode()
            return PowersetMode(base_mode=base, location=loc)

        if self._match_keyword('REF') or self._match_builtin('PTR'):
            free = bool(self._match_keyword('FREE'))
            target = self._parse_mode()
            return RefMode(target_mode=target, free=free, location=loc)

        if self._match_keyword('STRUCT'):
            self._expect(TokenType.LPAREN)
            fields = []
            if not self._check(TokenType.RPAREN):
                fields.append(self._parse_struct_field())
                while self._match(TokenType.COMMA):
                    fields.append(self._parse_struct_field())
            self._expect(TokenType.RPAREN)
            return StructMode(fields=fields, location=loc)

        if self._match_keyword('ARRAY'):
            self._expect(TokenType.LPAREN)
            # Index can be a range or mode
            if self._check_keyword('RANGE') or self._check(TokenType.INTEGER):
                lower = self._parse_expression()
                self._expect(TokenType.COLON)
                upper = self._parse_expression()
                index_mode = RangeMode(lower=lower, upper=upper, location=loc)
            else:
                index_mode = self._parse_mode()
            self._expect(TokenType.RPAREN)
            element_mode = self._parse_mode()
            layout = None
            if self._match_keyword('PACK'):
                layout = 'PACK'
            elif self._match_keyword('NOPACK'):
                layout = 'NOPACK'
            return ArrayMode(index_mode=index_mode, element_mode=element_mode, layout=layout, location=loc)

        if self._match_keyword('PROC'):
            parameters = []
            if self._match(TokenType.LPAREN):
                if not self._check(TokenType.RPAREN):
                    parameters = self._parse_parameters()
                self._expect(TokenType.RPAREN)
            returns = None
            if self._match_keyword('RETURNS'):
                self._expect(TokenType.LPAREN)
                returns = self._parse_mode()
                self._expect(TokenType.RPAREN)
            exceptions = []
            if self._match_keyword('EXCEPTIONS'):
                self._expect(TokenType.LPAREN)
                exceptions.append(self._expect(TokenType.IDENTIFIER).value)
                while self._match(TokenType.COMMA):
                    exceptions.append(self._expect(TokenType.IDENTIFIER).value)
                self._expect(TokenType.RPAREN)
            return ProcMode(parameters=parameters, returns=returns, exceptions=exceptions, location=loc)

        if self._match_keyword('BUFFER'):
            self._expect(TokenType.LPAREN)
            size = self._parse_expression()
            self._expect(TokenType.RPAREN)
            element_mode = self._parse_mode()
            return BufferMode(size=size, element_mode=element_mode, location=loc)

        if self._match_keyword('EVENT'):
            return EventMode(location=loc)

        if self._match_builtin('DURATION'):
            return DurationMode(location=loc)

        if self._match_builtin('TIME'):
            return TimeMode(location=loc)

        # Named mode (user-defined type reference)
        if self._check(TokenType.IDENTIFIER):
            name = self._advance().value
            return NamedMode(name=name, location=loc)

        raise ParseError(f"Expected mode, got {self.current.value}", self.current)

    def _parse_struct_field(self) -> StructField:
        """Parse struct field: name1, name2 mode"""
        loc = self._location()
        names = [self._expect(TokenType.IDENTIFIER).value]
        while self._match(TokenType.COMMA):
            if self._check(TokenType.IDENTIFIER):
                next_tok = self._peek(1)
                if next_tok.type == TokenType.COMMA:
                    # More names coming
                    names.append(self._advance().value)
                else:
                    # Check if current identifier is a builtin/keyword mode
                    if self._check_builtin('INT', 'BOOL', 'CHAR', 'DURATION', 'TIME',
                                           'PTR', 'FLOAT', 'BYTE', 'UBYTE', 'UINT',
                                           'LONG', 'ULONG', 'REAL', 'LONG_REAL', 'WCHAR'):
                        break
                    elif self._check_keyword('CHARS', 'BOOLS', 'SET', 'RANGE', 'POWERSET',
                                             'REF', 'STRUCT', 'ARRAY', 'PROC', 'BUFFER', 'EVENT'):
                        break
                    else:
                        # Assume it's another variable name
                        names.append(self._advance().value)
            else:
                break
        mode = self._parse_mode()
        return StructField(names=names, mode=mode, location=loc)

    # ========================================================================
    # Statements
    # ========================================================================

    def _parse_statement(self) -> Optional[Statement]:
        """Parse a statement"""
        loc = self._location()

        # Check for label
        label = None
        if self._check(TokenType.IDENTIFIER) and self._peek(1).type == TokenType.COLON:
            # Could be label or named procedure - peek further
            after = self._peek(2)
            if after.type != TokenType.KEYWORD or after.value not in ('PROC', 'PROCESS'):
                label = self._advance().value
                self._advance()  # consume colon

        stmt = self._parse_statement_body()
        if stmt and label:
            stmt.label = label
        return stmt

    def _parse_statement_body(self) -> Optional[Statement]:
        """Parse statement without label handling"""
        loc = self._location()

        # Empty statement
        if self._match(TokenType.SEMICOLON):
            return EmptyStmt(location=loc)

        # Control structures
        if self._check_keyword('IF'):
            return self._parse_if_stmt()

        if self._check_keyword('CASE'):
            return self._parse_case_stmt()

        if self._check_keyword('DO'):
            return self._parse_do_stmt()

        if self._check_keyword('BEGIN'):
            return self._parse_begin_block()

        # Simple statements
        if self._match_keyword('EXIT'):
            target = None
            if self._check(TokenType.IDENTIFIER):
                target = self._advance().value
            self._expect(TokenType.SEMICOLON)
            return ExitStmt(target=target, location=loc)

        if self._match_keyword('RETURN'):
            value = None
            if not self._check(TokenType.SEMICOLON):
                value = self._parse_expression()
            self._expect(TokenType.SEMICOLON)
            return ReturnStmt(value=value, location=loc)

        if self._match_keyword('RESULT'):
            value = self._parse_expression()
            self._expect(TokenType.SEMICOLON)
            return ResultStmt(value=value, location=loc)

        if self._match_keyword('GOTO'):
            target = self._expect(TokenType.IDENTIFIER).value
            self._expect(TokenType.SEMICOLON)
            return GotoStmt(target=target, location=loc)

        if self._match_keyword('STOP'):
            self._expect(TokenType.SEMICOLON)
            return StopStmt(location=loc)

        if self._match_keyword('ASSERT'):
            condition = self._parse_expression()
            self._expect(TokenType.SEMICOLON)
            return AssertStmt(condition=condition, location=loc)

        if self._match_keyword('CAUSE'):
            exception = self._expect(TokenType.IDENTIFIER).value
            self._expect(TokenType.SEMICOLON)
            return CauseStmt(exception=exception, location=loc)

        if self._check_keyword('SEND'):
            return self._parse_send_stmt()

        if self._check_keyword('RECEIVE'):
            return self._parse_receive_stmt()

        if self._check_keyword('DELAY'):
            return self._parse_delay_stmt()

        if self._check_keyword('START'):
            return self._parse_start_stmt()

        if self._match_keyword('CONTINUE'):
            event = self._parse_expression()
            self._expect(TokenType.SEMICOLON)
            return ContinueStmt(event=event, location=loc)

        # Assignment or procedure call
        return self._parse_assign_or_call()

    def _parse_if_stmt(self) -> IfStmt:
        """Parse IF condition THEN stmts [ELSIF ...] [ELSE stmts] FI"""
        loc = self._location()
        self._expect_keyword('IF')

        condition = self._parse_expression()
        self._expect_keyword('THEN')

        then_stmts = []
        while not self._check_keyword('ELSIF', 'ELSE', 'FI') and not self._check(TokenType.EOF):
            stmt = self._parse_statement()
            if stmt:
                then_stmts.append(stmt)

        elsif_parts = []
        while self._match_keyword('ELSIF'):
            elsif_loc = self._location()
            elsif_cond = self._parse_expression()
            self._expect_keyword('THEN')
            elsif_stmts = []
            while not self._check_keyword('ELSIF', 'ELSE', 'FI') and not self._check(TokenType.EOF):
                stmt = self._parse_statement()
                if stmt:
                    elsif_stmts.append(stmt)
            elsif_parts.append(ElsifPart(condition=elsif_cond, statements=elsif_stmts, location=elsif_loc))

        else_stmts = []
        if self._match_keyword('ELSE'):
            while not self._check_keyword('FI') and not self._check(TokenType.EOF):
                stmt = self._parse_statement()
                if stmt:
                    else_stmts.append(stmt)

        self._expect_keyword('FI')
        self._expect(TokenType.SEMICOLON)

        return IfStmt(
            condition=condition,
            then_stmts=then_stmts,
            elsif_parts=elsif_parts,
            else_stmts=else_stmts,
            location=loc
        )

    def _parse_case_stmt(self) -> CaseStmt:
        """Parse CASE selector OF (values): stmts; ... [ELSE stmts] ESAC"""
        loc = self._location()
        self._expect_keyword('CASE')

        selector = self._parse_expression()
        self._expect_keyword('OF')

        alternatives = []
        else_stmts = []

        while not self._check_keyword('ELSE', 'ESAC') and not self._check(TokenType.EOF):
            alt = self._parse_case_alternative()
            if alt:
                alternatives.append(alt)

        if self._match_keyword('ELSE'):
            while not self._check_keyword('ESAC') and not self._check(TokenType.EOF):
                stmt = self._parse_statement()
                if stmt:
                    else_stmts.append(stmt)

        self._expect_keyword('ESAC')
        self._expect(TokenType.SEMICOLON)

        return CaseStmt(selector=selector, alternatives=alternatives, else_stmts=else_stmts, location=loc)

    def _parse_case_alternative(self) -> Optional[CaseAlternative]:
        """Parse (value1, value2): statements;"""
        if not self._match(TokenType.LPAREN):
            return None

        loc = self._location()
        values = [self._parse_expression()]
        while self._match(TokenType.COMMA):
            values.append(self._parse_expression())
        self._expect(TokenType.RPAREN)
        self._expect(TokenType.COLON)

        statements = []
        while not self._check(TokenType.LPAREN) and not self._check_keyword('ELSE', 'ESAC') and not self._check(TokenType.EOF):
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)

        return CaseAlternative(values=values, statements=statements, location=loc)

    def _parse_do_stmt(self) -> Statement:
        """Parse DO loop variants"""
        loc = self._location()
        self._expect_keyword('DO')

        # DO EVER
        if self._match_keyword('EVER'):
            self._expect(TokenType.SEMICOLON)
            statements = []
            while not self._check_keyword('OD') and not self._check(TokenType.EOF):
                stmt = self._parse_statement()
                if stmt:
                    statements.append(stmt)
            self._expect_keyword('OD')
            self._expect(TokenType.SEMICOLON)
            return DoEverStmt(statements=statements, location=loc)

        # DO WHILE
        if self._match_keyword('WHILE'):
            condition = self._parse_expression()
            self._expect(TokenType.SEMICOLON)
            statements = []
            while not self._check_keyword('OD') and not self._check(TokenType.EOF):
                stmt = self._parse_statement()
                if stmt:
                    statements.append(stmt)
            self._expect_keyword('OD')
            self._expect(TokenType.SEMICOLON)
            return DoWhileStmt(condition=condition, statements=statements, location=loc)

        # DO FOR var := start TO/DOWN end [BY step]
        if self._match_keyword('FOR'):
            var = self._expect(TokenType.IDENTIFIER).value
            self._expect(TokenType.ASSIGN)
            start = self._parse_expression()

            down = bool(self._match_keyword('DOWN'))
            self._expect_keyword('TO')
            end = self._parse_expression()

            step = None
            if self._match_keyword('BY'):
                step = self._parse_expression()

            self._expect(TokenType.SEMICOLON)

            statements = []
            while not self._check_keyword('OD') and not self._check(TokenType.EOF):
                stmt = self._parse_statement()
                if stmt:
                    statements.append(stmt)

            self._expect_keyword('OD')
            self._expect(TokenType.SEMICOLON)

            return DoForStmt(var=var, start=start, end=end, step=step, down=down,
                           statements=statements, location=loc)

        # Plain DO ... OD block
        self._expect(TokenType.SEMICOLON)
        statements = []
        while not self._check_keyword('OD') and not self._check(TokenType.EOF):
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)
        self._expect_keyword('OD')
        self._expect(TokenType.SEMICOLON)
        return DoEverStmt(statements=statements, location=loc)

    def _parse_begin_block(self) -> BeginEndBlock:
        """Parse BEGIN declarations; statements END"""
        loc = self._location()
        self._expect_keyword('BEGIN')

        declarations = []
        statements = []

        # Declarations come first
        while self._is_declaration_start():
            decl = self._parse_declaration()
            if decl:
                declarations.append(decl)

        # Then statements
        while not self._check_keyword('END') and not self._check(TokenType.EOF):
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)

        self._expect_keyword('END')
        self._expect(TokenType.SEMICOLON)

        return BeginEndBlock(declarations=declarations, statements=statements, location=loc)

    def _parse_send_stmt(self) -> SendStmt:
        """Parse SEND signal(args) [TO process]"""
        loc = self._location()
        self._expect_keyword('SEND')

        signal = self._expect(TokenType.IDENTIFIER).value

        arguments = []
        if self._match(TokenType.LPAREN):
            if not self._check(TokenType.RPAREN):
                arguments.append(self._parse_expression())
                while self._match(TokenType.COMMA):
                    arguments.append(self._parse_expression())
            self._expect(TokenType.RPAREN)

        destination = None
        if self._match_keyword('TO'):
            destination = self._parse_expression()

        self._expect(TokenType.SEMICOLON)

        return SendStmt(signal=signal, arguments=arguments, destination=destination, location=loc)

    def _parse_receive_stmt(self) -> Statement:
        """Parse RECEIVE or RECEIVE CASE"""
        loc = self._location()
        self._expect_keyword('RECEIVE')

        if self._match_keyword('CASE'):
            # RECEIVE CASE
            alternatives = []
            else_stmts = []

            while self._match(TokenType.LPAREN):
                alt = self._parse_receive_alternative()
                alternatives.append(alt)

            if self._match_keyword('ELSE'):
                while not self._check_keyword('ESAC') and not self._check(TokenType.EOF):
                    stmt = self._parse_statement()
                    if stmt:
                        else_stmts.append(stmt)

            self._expect_keyword('ESAC')
            self._expect(TokenType.SEMICOLON)

            return ReceiveCaseStmt(alternatives=alternatives, else_stmts=else_stmts, location=loc)

        # Simple receive - treat as expression statement
        buffer = self._parse_expression()
        self._expect(TokenType.SEMICOLON)
        # Wrap in a call statement for now
        return CallStmt(proc=Identifier(name='RECEIVE'), arguments=[buffer], location=loc)

    def _parse_receive_alternative(self) -> ReceiveAlternative:
        """Parse (signal IN params): statements"""
        loc = self._location()
        signal = self._expect(TokenType.IDENTIFIER).value

        parameters = []
        if self._match_keyword('IN'):
            parameters.append(self._expect(TokenType.IDENTIFIER).value)
            while self._match(TokenType.COMMA):
                parameters.append(self._expect(TokenType.IDENTIFIER).value)

        self._expect(TokenType.RPAREN)
        self._expect(TokenType.COLON)

        statements = []
        while not self._check(TokenType.LPAREN) and not self._check_keyword('ELSE', 'ESAC') and not self._check(TokenType.EOF):
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)

        return ReceiveAlternative(signal=signal, parameters=parameters, statements=statements, location=loc)

    def _parse_delay_stmt(self) -> DelayStmt:
        """Parse DELAY duration"""
        loc = self._location()
        self._expect_keyword('DELAY')

        duration = None
        if not self._check(TokenType.SEMICOLON):
            duration = self._parse_expression()

        self._expect(TokenType.SEMICOLON)
        return DelayStmt(duration=duration, location=loc)

    def _parse_start_stmt(self) -> StartStmt:
        """Parse START process(args)"""
        loc = self._location()
        self._expect_keyword('START')

        process = self._expect(TokenType.IDENTIFIER).value

        arguments = []
        if self._match(TokenType.LPAREN):
            if not self._check(TokenType.RPAREN):
                arguments.append(self._parse_expression())
                while self._match(TokenType.COMMA):
                    arguments.append(self._parse_expression())
            self._expect(TokenType.RPAREN)

        self._expect(TokenType.SEMICOLON)
        return StartStmt(process=process, arguments=arguments, location=loc)

    def _parse_assign_or_call(self) -> Statement:
        """Parse assignment or procedure call"""
        loc = self._location()

        # Parse left side (could be location or procedure)
        expr = self._parse_expression()

        # Check for assignment
        if self._match(TokenType.ASSIGN):
            value = self._parse_expression()
            self._expect(TokenType.SEMICOLON)
            return AssignStmt(targets=[expr], value=value, location=loc)

        # Multiple assignment target
        if self._match(TokenType.COMMA):
            targets = [expr]
            targets.append(self._parse_expression())
            while self._match(TokenType.COMMA):
                targets.append(self._parse_expression())
            self._expect(TokenType.ASSIGN)
            value = self._parse_expression()
            self._expect(TokenType.SEMICOLON)
            return AssignStmt(targets=targets, value=value, location=loc)

        # Must be a procedure call
        self._expect(TokenType.SEMICOLON)

        # Extract proc and args from ProcCall expression
        if isinstance(expr, ProcCall):
            return CallStmt(proc=expr.proc, arguments=expr.arguments, location=loc)
        else:
            # Plain identifier call with no args
            return CallStmt(proc=expr, arguments=[], location=loc)

    # ========================================================================
    # Expressions
    # ========================================================================

    def _parse_expression(self) -> Expression:
        """Parse expression with precedence climbing"""
        return self._parse_precedence(1)

    def _parse_precedence(self, min_prec: int) -> Expression:
        """Precedence climbing parser"""
        left = self._parse_unary()

        while True:
            op = self._get_binary_op()
            if op is None:
                break

            prec = self.PRECEDENCE.get(op, 0)
            if prec < min_prec:
                break

            self._advance()  # consume operator

            # Right associative for **
            next_prec = prec + 1 if op != '**' else prec
            right = self._parse_precedence(next_prec)

            left = BinaryOp(op=op, left=left, right=right, location=left.location)

        return left

    def _get_binary_op(self) -> Optional[str]:
        """Get binary operator from current token"""
        # Map token types to operator strings
        op_map = {
            TokenType.PLUS: '+',
            TokenType.MINUS: '-',
            TokenType.STAR: '*',
            TokenType.SLASH: '/',
            TokenType.POWER: '**',
            TokenType.EQ: '=',
            TokenType.NE: '/=',
            TokenType.LT: '<',
            TokenType.GT: '>',
            TokenType.LE: '<=',
            TokenType.GE: '>=',
            TokenType.CONCAT: '//',
        }
        if self.current.type in op_map:
            return op_map[self.current.type]
        if self._check_keyword('AND', 'OR', 'XOR', 'MOD', 'REM', 'IN'):
            return self.current.value
        return None

    def _parse_unary(self) -> Expression:
        """Parse unary expression"""
        loc = self._location()

        if self._match_keyword('NOT'):
            operand = self._parse_unary()
            return UnaryOp(op='NOT', operand=operand, location=loc)

        if self._check(TokenType.MINUS):
            self._advance()
            operand = self._parse_unary()
            return UnaryOp(op='-', operand=operand, location=loc)

        if self._check(TokenType.PLUS):
            self._advance()
            operand = self._parse_unary()
            return UnaryOp(op='+', operand=operand, location=loc)

        return self._parse_postfix()

    def _parse_postfix(self) -> Expression:
        """Parse postfix operations (calls, indexing, field access)"""
        expr = self._parse_primary()

        while True:
            loc = self._location()

            # Function call or array access
            if self._match(TokenType.LPAREN):
                if self._check(TokenType.RPAREN):
                    self._advance()
                    expr = ProcCall(proc=expr, arguments=[], location=loc)
                else:
                    # Could be slice (x:y) or regular args
                    first = self._parse_expression()
                    if self._match(TokenType.COLON):
                        # Slice access
                        end = self._parse_expression()
                        self._expect(TokenType.RPAREN)
                        expr = SliceAccess(array=expr, start=first, end=end, location=loc)
                    else:
                        # Regular call/index - use ProcCall for both
                        # The semantic analyzer will determine if it's array access
                        args = [first]
                        while self._match(TokenType.COMMA):
                            args.append(self._parse_expression())
                        self._expect(TokenType.RPAREN)
                        # Always use ProcCall - semantic analyzer resolves ambiguity
                        expr = ProcCall(proc=expr, arguments=args, location=loc)

            # Field access
            elif self._match(TokenType.DOT):
                field = self._expect(TokenType.IDENTIFIER).value
                expr = FieldAccess(struct=expr, field=field, location=loc)

            # Dereference
            elif self._match(TokenType.ARROW):
                expr = DerefAccess(ref=expr, location=loc)

            else:
                break

        return expr

    def _parse_primary(self) -> Expression:
        """Parse primary expression"""
        loc = self._location()

        # Literals
        if self._check(TokenType.INTEGER):
            value = int(self._advance().value)
            return Literal(value=value, kind='int', location=loc)

        if self._check(TokenType.REAL):
            value = float(self._advance().value)
            return Literal(value=value, kind='float', location=loc)

        if self._check(TokenType.STRING):
            value = self._advance().value
            return Literal(value=value, kind='string', location=loc)

        if self._check(TokenType.CHAR):
            value = self._advance().value
            return Literal(value=value, kind='char', location=loc)

        if self._check(TokenType.BINARY):
            value = int(self._advance().value, 2)
            return Literal(value=value, kind='int', location=loc)

        if self._check(TokenType.HEX):
            value = int(self._advance().value, 16)
            return Literal(value=value, kind='int', location=loc)

        if self._check(TokenType.OCTAL):
            value = int(self._advance().value, 8)
            return Literal(value=value, kind='int', location=loc)

        # Boolean literals (predefined names)
        if self._match_builtin('TRUE'):
            return Literal(value=True, kind='bool', location=loc)
        if self._match_builtin('FALSE'):
            return Literal(value=False, kind='bool', location=loc)

        # NULL (predefined name)
        if self._match_builtin('NULL'):
            return Literal(value=None, kind='null', location=loc)

        # Parenthesized expression
        if self._match(TokenType.LPAREN):
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return expr

        # IF expression
        if self._check_keyword('IF'):
            return self._parse_if_expr()

        # CASE expression
        if self._check_keyword('CASE'):
            return self._parse_case_expr()

        # START expression
        if self._match_keyword('START'):
            process = self._expect(TokenType.IDENTIFIER).value
            arguments = []
            if self._match(TokenType.LPAREN):
                if not self._check(TokenType.RPAREN):
                    arguments.append(self._parse_expression())
                    while self._match(TokenType.COMMA):
                        arguments.append(self._parse_expression())
                self._expect(TokenType.RPAREN)
            return StartExpr(process=process, arguments=arguments, location=loc)

        # RECEIVE expression
        if self._match_keyword('RECEIVE'):
            buffer = self._parse_primary()
            return ReceiveExpr(buffer=buffer, location=loc)

        # Builtin calls
        if self._check(TokenType.BUILTIN):
            name = self._advance().value
            arguments = []
            if self._match(TokenType.LPAREN):
                if not self._check(TokenType.RPAREN):
                    arguments.append(self._parse_expression())
                    while self._match(TokenType.COMMA):
                        arguments.append(self._parse_expression())
                self._expect(TokenType.RPAREN)
            return BuiltinCall(name=name, arguments=arguments, location=loc)

        # Identifier
        if self._check(TokenType.IDENTIFIER):
            name = self._advance().value
            return Identifier(name=name, location=loc)

        raise ParseError(f"Unexpected token in expression: {self.current.value}", self.current)

    def _parse_if_expr(self) -> IfExpr:
        """Parse IF condition THEN expr ELSE expr FI"""
        loc = self._location()
        self._expect_keyword('IF')
        condition = self._parse_expression()
        self._expect_keyword('THEN')
        then_expr = self._parse_expression()
        self._expect_keyword('ELSE')
        else_expr = self._parse_expression()
        self._expect_keyword('FI')
        return IfExpr(condition=condition, then_expr=then_expr, else_expr=else_expr, location=loc)

    def _parse_case_expr(self) -> CaseExpr:
        """Parse CASE expression"""
        loc = self._location()
        self._expect_keyword('CASE')
        selector = self._parse_expression()
        self._expect_keyword('OF')

        alternatives = []
        while self._match(TokenType.LPAREN):
            alt_loc = self._location()
            values = [self._parse_expression()]
            while self._match(TokenType.COMMA):
                values.append(self._parse_expression())
            self._expect(TokenType.RPAREN)
            self._expect(TokenType.COLON)
            # For case expression, each alternative has single expression
            stmt = self._parse_expression()
            # Store as CaseAlternative but with expression as single-item statement list
            # This is a simplification
            alternatives.append(CaseAlternative(values=values, statements=[stmt], location=alt_loc))
            self._match(TokenType.COMMA)  # Optional comma between alternatives

        else_expr = None
        if self._match_keyword('ELSE'):
            else_expr = self._parse_expression()

        self._expect_keyword('ESAC')
        return CaseExpr(selector=selector, alternatives=alternatives, else_expr=else_expr, location=loc)


def parse(source: str, filename: str = "<unknown>") -> Program:
    """Convenience function to parse CHILL source"""
    parser = Parser(source, filename)
    return parser.parse()

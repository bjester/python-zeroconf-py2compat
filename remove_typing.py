import sys
from six.moves import cStringIO

import ast
import astunparse


class Parser(ast.NodeTransformer):
    """
    Based off https://stackoverflow.com/questions/42733877/remove-type-hints-in-python-source-programmatically
    """
    def visit_FunctionDef(self, node):
        # remove the return type definition
        node.returns = None
        # remove all argument annotations
        if node.args.args:
            # remove single args annotations
            for arg in node.args.args:
                arg.annotation = None
            # remove single kwargs annotations
            for kwarg in node.args.kwonlyargs:
                kwarg.annotation = None
            # remove variable args annotations
            if node.args.vararg:
                node.args.vararg.annotation = None
            # remove variable kwargs annotations
            if node.args.kwarg:
                node.args.kwarg.annotation = None

        return node

    def visit_Import(self, node):
        # remove typing import
        node.names = [n for n in node.names if n.name != 'typing']
        return node if node.names else None

    def visit_ImportFrom(self, node):
        # remove typing import
        return node if node.module != 'typing' else None


class DocString(object):
    def __init__(self, value):
        self.value = value


class Writer(astunparse.Unparser):
    def _replace_docstring(self, node):
        # format the doc string
        doc_str = ast.get_docstring(node)
        if doc_str is not None:
            node.body[0].value = DocString(doc_str)

    def _Module(self, node):
        self._replace_docstring(node)
        return super(Writer, self)._Module(node)

    def _ClassDef(self, node):
        self._replace_docstring(node)
        return super(Writer, self)._ClassDef(node)

    def _FunctionDef(self, node):
        self._replace_docstring(node)
        return super(Writer, self)._FunctionDef(node)

    def _DocString(self, doc_string):
        #
        self.write("{quotes}{doc_string}{quotes}".format(
            quotes='"""',
            doc_string=doc_string.value,
        ))

    def _Assign(self, node):
        # comment out `InterfacesType` type helper
        if isinstance(node.targets[0], ast.Name) and node.targets[0].id == "InterfacesType":
            node.targets[0].id = "# InterfacesType"
        super(Writer, self)._Assign(node)

    def _Call(self, node):
        # replace all `cast` function calls with their second argument
        if isinstance(node.func, ast.Name) and node.func.id == "cast":
            self.dispatch(node.args[1])
        else:
            super(Writer, self)._Call(node)


if __name__ == '__main__':
    try:
        with open(sys.argv[1], 'r') as source_file:
            # parse the source code into an AST
            parsed_source = ast.parse(source_file.read())
            # remove all type annotations, function return type definitions
            # and import statements from 'typing'
            remover = Parser()
            transformed = remover.visit(parsed_source)
            # convert the AST back to source code
            output = cStringIO()
            writer = Writer(transformed, file=output)
            print(output.getvalue())
    except IndexError:
        print("Missing source file path argument")

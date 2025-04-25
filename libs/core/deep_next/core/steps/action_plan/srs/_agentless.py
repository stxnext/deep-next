# The functions in this file come from the project "Agentless":
# https://github.com/OpenAutoCoder/Agentless
import ast
import os
import re
from pathlib import Path

import libcst as cst
import libcst.matchers as m


def create_structure(directory_path):
    """Create the structure of the repository directory by parsing Python files.

    :param directory_path: Path to the repository directory.
    :return: A dictionary representing the structure.
    """
    structure = {}

    for root, _, files in os.walk(directory_path):
        repo_name = os.path.basename(directory_path)
        relative_root = os.path.relpath(root, directory_path)

        if relative_root == ".":
            relative_root = repo_name

        curr_struct = structure

        for part in relative_root.split(os.sep):
            if part not in curr_struct:
                curr_struct[part] = {}

            curr_struct = curr_struct[part]

        for file_name in files:
            if file_name.endswith(".py"):
                file_path = os.path.join(root, file_name)
                class_info, function_names, file_lines = parse_python_file(file_path)

                curr_struct[file_name] = {
                    "classes": class_info,
                    "functions": function_names,
                    "text": file_lines,
                }
            else:
                curr_struct[file_name] = {}

    return structure


def parse_python_file(file_path, file_content=None):
    """
    Parse a python file to extract class and function defs with their line numbers.

    :param file_path: Path to the Python file.
    :return: Class names, function names, and file contents
    """
    if file_content is None:
        try:
            with open(file_path, "r") as file:
                file_content = file.read()
                parsed_data = ast.parse(file_content)
        except Exception as e:  # Catch all types of exceptions
            print(f"Error in file {file_path}: {e}")
            return [], [], ""
    else:
        try:
            parsed_data = ast.parse(file_content)
        except Exception as e:  # Catch all types of exceptions
            print(f"Error in file {file_path}: {e}")
            return [], [], ""

    class_info = []
    function_names = []
    class_methods = set()

    for node in ast.walk(parsed_data):
        if isinstance(node, ast.ClassDef):
            methods = []
            for n in node.body:
                if isinstance(n, ast.FunctionDef):
                    methods.append(
                        {
                            "name": n.name,
                            "start_line": n.lineno,
                            "end_line": n.end_lineno,
                            "text": file_content.splitlines()[
                                n.lineno - 1 : n.end_lineno
                            ],
                        }
                    )
                    class_methods.add(n.name)
            class_info.append(
                {
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "text": file_content.splitlines()[
                        node.lineno - 1 : node.end_lineno
                    ],
                    "methods": methods,
                }
            )
        elif isinstance(node, ast.FunctionDef) and not isinstance(
            node, ast.AsyncFunctionDef
        ):
            if node.name not in class_methods:
                function_names.append(
                    {
                        "name": node.name,
                        "start_line": node.lineno,
                        "end_line": node.end_lineno,
                        "text": file_content.splitlines()[
                            node.lineno - 1 : node.end_lineno
                        ],
                    }
                )

    return class_info, function_names, file_content.splitlines()


def get_repo_files(structure, filepaths: list[str | Path]):
    filepaths = [str(filepath) for filepath in filepaths]
    files, classes, functions = get_full_file_paths_and_classes_and_functions(structure)
    file_contents = dict()
    for filepath in filepaths:
        content = None

        for file_content in files:
            if file_content[0] == filepath:
                content = "\n".join(file_content[1])
                file_contents[filepath] = content
                break

        assert content is not None, "file not found"
    return file_contents


def get_full_file_paths_and_classes_and_functions(structure, current_path=""):
    """
    Recursively retrieve all file paths, classes, and functions in a directory structure

    Arguments:
    structure -- a dictionary representing the directory structure
    current_path -- the path accumulated so far, used during recursion (default="")

    Returns:
    A tuple containing:
    - files: list of full file paths
    - classes: list of class details with file paths
    - functions: list of function details with file paths
    """
    files = []
    classes = []
    functions = []
    for name, content in structure.items():
        if isinstance(content, dict):
            if (
                "functions" not in content.keys()
                and "classes" not in content.keys()
                and "text" not in content.keys()
            ) or not len(content.keys()) == 3:
                # or guards against case where functions and classes are
                # somehow part of the structure.
                next_path = f"{current_path}/{name}" if current_path else name
                (
                    sub_files,
                    sub_classes,
                    sub_functions,
                ) = get_full_file_paths_and_classes_and_functions(content, next_path)
                files.extend(sub_files)
                classes.extend(sub_classes)
                functions.extend(sub_functions)
            else:
                next_path = f"{current_path}/{name}" if current_path else name
                files.append((next_path, content["text"]))
                if "classes" in content:
                    for clazz in content["classes"]:
                        classes.append(
                            {
                                "file": next_path,
                                "name": clazz["name"],
                                "start_line": clazz["start_line"],
                                "end_line": clazz["end_line"],
                                "methods": [
                                    {
                                        "name": method["name"],
                                        "start_line": method["start_line"],
                                        "end_line": method["end_line"],
                                    }
                                    for method in clazz.get("methods", [])
                                ],
                            }
                        )
                if "functions" in content:
                    for function in content["functions"]:
                        function["file"] = next_path
                        functions.append(function)
        else:
            next_path = f"{current_path}/{name}" if current_path else name
            files.append(next_path)
    return files, classes, functions


def get_skeleton(
    raw_code,
    keep_constant: bool = True,
    keep_indent: bool = False,
    compress_assign: bool = False,
    total_lines=30,
    prefix_lines=10,
    suffix_lines=10,
):
    try:
        tree = cst.parse_module(raw_code)
    except:  # noqa E722
        return raw_code

    transformer = CompressTransformer(keep_constant=keep_constant, keep_indent=True)
    modified_tree = tree.visit(transformer)
    code = modified_tree.code

    if compress_assign:
        code = compress_assign_stmts(
            code,
            total_lines=total_lines,
            prefix_lines=prefix_lines,
            suffix_lines=suffix_lines,
        )

    if keep_indent:
        code = code.replace(CompressTransformer.replacement_string + "\n", "...\n")
        code = code.replace(CompressTransformer.replacement_string, "...\n")
    else:
        pattern = f"\\n[ \\t]*{CompressTransformer.replacement_string}"
        replacement = "\n..."
        code = re.sub(pattern, replacement, code)

    return code


class CompressTransformer(cst.CSTTransformer):
    DESCRIPTION = str = "Replaces function body with ..."
    replacement_string = '"__FUNC_BODY_REPLACEMENT_STRING__"'

    def __init__(self, keep_constant=True, keep_indent=False):
        self.keep_constant = keep_constant
        self.keep_indent = keep_indent

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        new_body = [
            stmt
            for stmt in updated_node.body
            if m.matches(stmt, m.ClassDef())
            or m.matches(stmt, m.FunctionDef())
            or (
                self.keep_constant
                and m.matches(stmt, m.SimpleStatementLine())
                and m.matches(stmt.body[0], m.Assign())
            )
        ]
        return updated_node.with_changes(body=new_body)

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        # Remove docstring in the class body
        new_body = [
            stmt
            for stmt in updated_node.body.body
            if not (
                m.matches(stmt, m.SimpleStatementLine())
                and m.matches(stmt.body[0], m.Expr())
                and m.matches(stmt.body[0].value, m.SimpleString())
            )
        ]
        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.CSTNode:
        if not self.keep_indent:
            # replace with unindented statement
            new_expr = cst.Expr(value=cst.SimpleString(value=self.replacement_string))
            new_body = cst.IndentedBlock((new_expr,))
            return updated_node.with_changes(body=new_body)
        else:
            # replace with indented statement
            # new_expr = [cst.Pass()]
            new_expr = [
                cst.Expr(value=cst.SimpleString(value=self.replacement_string)),
            ]
            return updated_node.with_changes(
                body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=new_expr)])
            )


class GlobalVariableVisitorParsing(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (cst.metadata.PositionProvider,)

    def __init__(self):
        self.assigns = []

    def leave_Assign(self, original_node: cst.Module):
        stmt = original_node
        start_pos = self.get_metadata(cst.metadata.PositionProvider, stmt).start
        end_pos = self.get_metadata(cst.metadata.PositionProvider, stmt).end
        self.assigns.append([stmt, start_pos, end_pos])


class GlobalVariableVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (cst.metadata.PositionProvider,)

    def __init__(self):
        self.global_assigns = []

    def leave_Module(self, original_node: cst.Module):
        assigns = []
        for stmt in original_node.body:
            if m.matches(stmt, m.SimpleStatementLine()) and m.matches(
                stmt.body[0], m.Assign()
            ):
                start_pos = self.get_metadata(cst.metadata.PositionProvider, stmt).start
                end_pos = self.get_metadata(cst.metadata.PositionProvider, stmt).end
                assigns.append([stmt, start_pos, end_pos])
        self.global_assigns.extend(assigns)


def remove_lines(raw_code, remove_line_intervals):
    # TODO: speed up this function
    # remove_line_intervals.sort()

    # Remove lines
    new_code = ""
    for i, line in enumerate(raw_code.splitlines()):
        # intervals are one-based
        if not any(start <= i + 1 <= end for start, end in remove_line_intervals):
            new_code += line + "\n"
        if any(start == i + 1 for start, _ in remove_line_intervals):
            new_code += "...\n"
    return new_code


def compress_assign_stmts(raw_code, total_lines=30, prefix_lines=10, suffix_lines=10):
    try:
        tree = cst.parse_module(raw_code)
    except Exception as e:
        print(e.__class__.__name__, e)
        return raw_code

    wrapper = cst.metadata.MetadataWrapper(tree)
    visitor = GlobalVariableVisitorParsing()
    wrapper.visit(visitor)

    remove_line_intervals = []
    for stmt in visitor.assigns:
        if stmt[2].line - stmt[1].line > total_lines:
            remove_line_intervals.append(
                (stmt[1].line + prefix_lines, stmt[2].line - suffix_lines)
            )
    return remove_lines(raw_code, remove_line_intervals)


def extract_locs_for_files(locs, file_names, keep_old_order=False):
    if keep_old_order:
        results = {fn: [] for fn in file_names}
    else:
        results = {}  # dict is insertion ordered
    current_file_name = None
    for loc in locs:
        for line in loc.splitlines():
            if line.strip().endswith(".py"):
                current_file_name = line.strip()
            elif line.strip() and any(
                line.startswith(w)
                for w in ["line:", "function:", "class:", "variable:"]
            ):
                if current_file_name in file_names:
                    if current_file_name not in results:
                        results[current_file_name] = []
                    results[current_file_name].append(line)
                else:
                    pass

    for file_name in file_names:
        if file_name not in results:  # guard for new order case
            results[file_name] = []

    return {fn: "\n".join(results[fn]) for fn in results.keys()}


def construct_topn_file_context(
    file_to_locs,
    pred_files,
    file_contents,
    structure,
    context_window: int,
    loc_interval: bool = True,
    fine_grain_loc_only: bool = False,
    add_space: bool = False,
    sticky_scroll: bool = False,
    no_line_number: bool = False,
):
    """Concatenate provided locations to form a context.

    loc: {"file_name_1": ["loc_str_1"], ...}
    """
    file_loc_intervals = dict()
    topn_content = ""

    for pred_file, locs in file_to_locs.items():
        content = file_contents[pred_file]
        line_locs, context_intervals = transfer_arb_locs_to_locs(
            locs,
            structure,
            pred_file,
            context_window,
            loc_interval,
            fine_grain_loc_only,
            file_content=file_contents[pred_file] if pred_file in file_contents else "",
        )

        if len(line_locs) > 0:
            # Note that if no location is predicted, we exclude this file.
            file_loc_content = line_wrap_content(
                content,
                context_intervals,
                add_space=add_space,
                no_line_number=no_line_number,
                sticky_scroll=sticky_scroll,
            )
            topn_content += f"### {pred_file}\n{file_loc_content}\n\n\n"
            file_loc_intervals[pred_file] = context_intervals

    return topn_content, file_loc_intervals


def transfer_arb_locs_to_locs(
    locs,
    structure,
    pred_file,
    context_window=10,
    loc_interval=True,
    fine_grain_only=False,
    remove_line=False,
    file_content="",
    verbose=False,
) -> tuple[list, list]:
    if structure is None:
        class_info, function_names, file_lines = parse_python_file("", file_content)
        structure = {}
        structure[pred_file] = {
            "classes": class_info,
            "functions": function_names,
            "text": file_lines,
        }

    files, classes, functions = get_full_file_paths_and_classes_and_functions(structure)

    line_loc = []
    if isinstance(locs, str):
        # if its a single loc
        locs = [locs]
    # TODO: parse it in advance
    global_vars = parse_global_var_from_code(file_content)
    unrecognized_locs = []

    for model_pred_locs in locs:
        current_class_name = ""
        for loc in model_pred_locs.splitlines():
            # handle cases like "class: MyClass.my_method"
            if loc.startswith("class: ") and "." not in loc:
                loc = loc[len("class: ") :].strip()
                relevant_class = [
                    clazz
                    for clazz in classes
                    if clazz["file"] == pred_file and clazz["name"] == loc
                ]

                if len(relevant_class) == 0:
                    unrecognized_locs.append(loc)
                else:
                    line_loc.append(
                        (relevant_class[0]["start_line"], relevant_class[0]["end_line"])
                    )
                    current_class_name = loc

            elif loc.startswith("function: ") or "." in loc:
                loc = loc.split(":", 1)[-1].strip()

                if "." in loc:
                    # assume its a method within a class
                    method_name = loc.split(".")[1]
                    class_name = loc.split(".")[0]

                    relevant_class = [
                        clazz
                        for clazz in classes
                        if clazz["file"] == pred_file and clazz["name"] == class_name
                    ]
                    if len(relevant_class) == 0:
                        unrecognized_locs.append(loc)
                    else:
                        relevant_method = [
                            method
                            for method in relevant_class[0]["methods"]
                            if method["name"] == method_name
                        ]
                        if len(relevant_method) == 0:
                            unrecognized_locs.append(loc)
                        else:
                            line_loc.append(
                                (
                                    relevant_method[0]["start_line"],
                                    relevant_method[0]["end_line"],
                                )
                            )

                else:
                    relevant_function = [
                        function
                        for function in functions
                        if function["file"] == pred_file and function["name"] == loc
                    ]
                    if len(relevant_function) == 0:
                        if current_class_name != "":
                            # check if its a method
                            relevant_class = [
                                clazz
                                for clazz in classes
                                if clazz["file"] == pred_file
                                and clazz["name"] == current_class_name
                            ]
                            relevant_method = [
                                method
                                for method in relevant_class[0]["methods"]
                                if method["name"] == loc
                            ]
                            if len(relevant_method) == 0:
                                unrecognized_locs.append(loc)
                            else:
                                line_loc.append(
                                    (
                                        relevant_method[0]["start_line"],
                                        relevant_method[0]["end_line"],
                                    )
                                )
                        else:
                            # look for it in any class
                            relevant_method = []
                            for clazz in classes:
                                if clazz["file"] == pred_file:
                                    relevant_method.extend(
                                        [
                                            method
                                            for method in clazz["methods"]
                                            if method["name"] == loc
                                        ]
                                    )

                            if len(relevant_method) == 1:
                                line_loc.append(
                                    (
                                        relevant_method[0]["start_line"],
                                        relevant_method[0]["end_line"],
                                    )
                                )
                    else:
                        line_loc.append(
                            (
                                relevant_function[0]["start_line"],
                                relevant_function[0]["end_line"],
                            )
                        )
            elif loc.startswith("line: "):
                if remove_line:
                    # TODO: can recover the corresponding function instead of
                    # throwing it away
                    continue
                loc = loc[len("line: ") :].strip().split()[0]
                try:
                    # line_loc.append(int(loc))
                    line_loc.append((int(loc), int(loc)))
                except:  # noqa E722
                    continue
            elif loc.startswith("variable:"):
                vars = loc[len("variable:") :].strip().split()
                for v in vars:
                    if v in global_vars:
                        line_loc.append(
                            (global_vars[v]["start_line"], global_vars[v]["end_line"])
                        )
            else:
                if loc.strip():
                    unrecognized_locs.append(loc)
                # assert False

    # Fine-grained-only loc: Remove intervals that are supersets of another.
    if fine_grain_only:
        filtered_line_loc = []
        for st, en in line_loc:
            if filtered_line_loc:
                last_st, last_en = filtered_line_loc[-1]
                # If the current interval is a more fine-grained loc,
                # remove the superset.
                if last_st <= st and en <= last_en:
                    filtered_line_loc.pop()
            filtered_line_loc.append((st, en))
        line_loc = filtered_line_loc

    # compute max min
    # TODO: think of strategies to do bunched up lines
    # TODO: e.g., we can have multiple code segments (right now, its just one)

    for file_content in files:
        if file_content[0] == pred_file:
            content = file_content[1]
            break

    if len(line_loc) == 0:
        return [], []

    # max_line = min(max(line_loc) + context_window, len(content))
    # min_line = max(min(line_loc) - context_window, 0)
    #
    # return line_loc, max_line, min_line

    if verbose:
        print("Unrecognized locs:")
        for loc in unrecognized_locs:
            print(loc)

    # compute overlapping locations instead
    if loc_interval:
        contextual_line_loc = []
        for loc in line_loc:
            # Clip the context window to the beginning and end of the file
            max_line = max(min(loc[1] + context_window, len(content)), 0)
            min_line = min(max(loc[0] - context_window, 0), len(content))
            contextual_line_loc.append((min_line, max_line))

        return line_loc, merge_intervals(contextual_line_loc)
    else:
        # defaulting to max min
        max_line = min(max([loc[1] for loc in line_loc]) + context_window, len(content))
        min_line = max(min([loc[0] for loc in line_loc]) - context_window, 0)

        return line_loc, [(min_line, max_line)]


def line_wrap_content(
    content: str,
    context_intervals=None,
    add_space=False,
    no_line_number=False,
    sticky_scroll=False,
):
    """Add n| to each line, where n increases"""

    def is_scope(line):
        # TODO: this might not be precise, can improve with syntax parsing
        return line.startswith("class ") or line.strip().startswith("def ")

    lines = content.split("\n")
    new_lines = []
    if context_intervals is None or context_intervals == []:
        context_intervals = [(0, len(lines))]

    prev_scopes = []
    line_format = "{line}"
    if not no_line_number:
        line_format = (
            "{line_number}|{line}" if not add_space else "{line_number}| {line} "
        )
    for interval in context_intervals:
        min_line, max_line = interval

        if min_line != 0:
            new_lines.append("...")

        scopes = []
        for i, line in enumerate(lines):
            if sticky_scroll:
                # add current line to scope if necessary
                if is_scope(line):
                    indent_level = len(line) - len(line.lstrip())
                    while scopes and scopes[-1]["indent_level"] >= indent_level:
                        scopes.pop()
                    scopes.append(
                        {"line": line, "line_number": i, "indent_level": indent_level}
                    )

            if min_line != -1 and i < min_line - 1:
                continue
            if sticky_scroll and i == min_line - 1:
                # add scope lines
                last_scope_line = None
                for j, scope_line in enumerate(scopes):
                    # don't repeat previous scopes
                    if (
                        len(prev_scopes) > j
                        and prev_scopes[j]["line_number"] == scope_line["line_number"]
                    ):
                        continue
                    # don't repeat current line
                    if i == scope_line["line_number"]:
                        continue
                    new_lines.append(
                        line_format.format(
                            line_number=scope_line["line_number"] + 1,
                            line=scope_line["line"],
                        )
                    )
                    last_scope_line = scope_line["line_number"]
                if last_scope_line is not None and last_scope_line < i - 1:
                    new_lines.append("...")

            new_lines.append(line_format.format(line_number=i + 1, line=line))
            if max_line != -1 and i >= max_line - 1:
                break
        prev_scopes = scopes

    if max_line != len(lines):
        new_lines.append("...")

    return "\n".join(new_lines)


def parse_global_var_from_code(file_content: str) -> dict[str, dict]:
    """Parse global variables."""
    try:
        tree = cst.parse_module(file_content)
    except:  # noqa E722
        return file_content

    wrapper = cst.metadata.MetadataWrapper(tree)
    visitor = GlobalVariableVisitor()
    wrapper.visit(visitor)

    global_assigns = {}
    for assign_stmt, start_pos, end_pos in visitor.global_assigns:
        for t in assign_stmt.body:
            try:
                targets = [t.targets[0].target.value]
            except:  # noqa E722
                try:
                    targets = t.targets[0].target.elements
                    targets = [x.value.value for x in targets]
                except:  # noqa E722
                    targets = []
            for target_var in targets:
                global_assigns[target_var] = {
                    "start_line": start_pos.line,
                    "end_line": end_pos.line,
                }
    return global_assigns


def merge_intervals(intervals):
    # intervals inclusive
    if not intervals:
        return []

    # Sort the intervals based on the starting value of each tuple
    intervals.sort(key=lambda interval: interval[0])

    merged_intervals = [intervals[0]]

    for current in intervals[1:]:
        last = merged_intervals[-1]

        # Check if there is overlap
        if current[0] <= last[1]:
            # If there is overlap, merge the intervals
            merged_intervals[-1] = (last[0], max(last[1], current[1]))
        else:
            # If there is no overlap, just add the current interval to the result list
            merged_intervals.append(current)

    return merged_intervals

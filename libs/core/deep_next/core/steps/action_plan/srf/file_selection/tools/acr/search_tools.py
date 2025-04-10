from collections import defaultdict, namedtuple
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import MutableMapping

from deep_next.core.steps.action_plan.srf.file_selection.tools.acr.utils import (
    catch_all_and_log,
    find_python_files,
    get_class_signature,
    get_code_region_containing_code,
    get_code_snippets,
    parse_python_file,
)

RESULT_SHOW_LIMIT = 3


LineRange = namedtuple("LineRange", ["start", "end"])

ClassIndexType = MutableMapping[str, list[tuple[str, LineRange]]]
ClassFuncIndexType = MutableMapping[
    str, MutableMapping[str, list[tuple[str, LineRange]]]
]
FuncIndexType = MutableMapping[str, list[tuple[str, LineRange]]]
ClassRelationIndexType = MutableMapping[str, list[str]]


@dataclass
class SearchResult:
    """Dataclass to hold search results."""

    # this is absolute path
    file_path: str
    # line numbers are 1-based
    start: int | None
    end: int | None
    class_name: str | None
    func_name: str | None
    code: str

    @staticmethod
    def to_relative_path(file_path: str, project_root: str) -> str:
        """Convert an absolute path to a path relative to the project root.

        Args:
            - file_path (str): The absolute path.
            - project_root (str): Absolute path of the project root dir.

        Returns:
            The relative path.
        """
        if Path(file_path).is_absolute():
            return str(Path(file_path).relative_to(project_root))
        else:
            return file_path

    def to_tagged_upto_file(self, project_root: str):
        """Convert the search result to a tagged string, upto file path."""
        rel_path = self.to_relative_path(self.file_path, project_root)
        file_part = f"<file>{rel_path}</file>"
        return file_part

    def to_tagged_upto_class(self, project_root: str):
        """Convert the search result to a tagged string, upto class."""
        prefix = self.to_tagged_upto_file(project_root)
        class_part = (
            f"<class>{self.class_name}</class>" if self.class_name is not None else ""
        )
        return f"{prefix}\n{class_part}"

    def to_tagged_upto_func(self, project_root: str):
        """Convert the search result to a tagged string, upto function."""
        prefix = self.to_tagged_upto_class(project_root)
        func_part = (
            f"<func>{self.func_name}</func>" if self.func_name is not None else ""
        )
        return f"{prefix}{func_part}"

    def to_tagged_str(self, project_root: str):
        """Convert the search result to a tagged string."""
        prefix = self.to_tagged_upto_func(project_root)
        code_part = f"<code>\n{self.code}\n</code>"
        return f"{prefix}\n{code_part}"

    @staticmethod
    def collapse_to_file_level(lst, project_root: str) -> str:
        """Collapse search results to file level."""
        res = dict()  # file -> count
        for r in lst:
            if r.file_path not in res:
                res[r.file_path] = 1
            else:
                res[r.file_path] += 1
        res_str = ""
        for file_path, count in res.items():
            rel_path = SearchResult.to_relative_path(file_path, project_root)
            file_part = f"<file>{rel_path}</file>"
            res_str += f"- {file_part} ({count} matches)\n"
        return res_str

    @staticmethod
    def collapse_to_method_level(lst, project_root: str) -> str:
        """Collapse search results to method level."""
        res = dict()  # file -> dict(method -> count)
        for r in lst:
            if r.file_path not in res:
                res[r.file_path] = dict()
            func_str = r.func_name if r.func_name is not None else "Not in a function"
            if func_str not in res[r.file_path]:
                res[r.file_path][func_str] = 1
            else:
                res[r.file_path][func_str] += 1
        res_str = ""
        for file_path, funcs in res.items():
            rel_path = SearchResult.to_relative_path(file_path, project_root)
            file_part = f"<file>{rel_path}</file>"
            for func, count in funcs.items():
                if func == "Not in a function":
                    func_part = func
                else:
                    func_part = f"<func>{func}</func>"
                res_str += f"- {file_part}{func_part} ({count} matches)\n"
        return res_str


class SearchBackend:
    def __init__(self, project_path: str):
        self.project_path = project_path
        # list of all files ending with .py, which are likely not test files
        # These are all ABSOLUTE paths.
        self.parsed_files: list[str] = []

        # for file name in the indexes, assume they are absolute path
        # class name -> [(file_name, line_range)]
        self.class_index: ClassIndexType = {}

        # {class_name -> {func_name -> [(file_name, line_range)]}}
        # inner dict is a list, since we can have (1) overloading func names,
        # and (2) multiple classes with the same name, having the same method
        self.class_func_index: ClassFuncIndexType = {}

        # a partially complete map of all the subclass relations
        # {class_name -> [class_name]}
        self.class_relation_index: ClassRelationIndexType = defaultdict(list)

        # function name -> [(file_name, line_range)]
        self.function_index: FuncIndexType = {}

        self._build_index()

    def _build_index(self):
        """
        With all source code of the project, build two indexes:

        1. From class name to (source file, start line, end line)
        2. From function name to (source file, start line, end line)

        Since there can be two classes/functions with the same name, the mapping
        value is a list of tuples.
        This is for fast lookup whenever we receive a query.
        """
        self._update_indices(*self._build_python_index(self.project_path))

    def _update_indices(
        self,
        class_index: ClassIndexType,
        class_func_index: ClassFuncIndexType,
        function_index: FuncIndexType,
        class_relation_index: ClassRelationIndexType,
        parsed_files: list[str],
    ) -> None:
        self.class_index.update(class_index)
        self.class_func_index.update(class_func_index)
        self.function_index.update(function_index)
        self.class_relation_index.update(class_relation_index)
        self.parsed_files.extend(parsed_files)

    @classmethod
    @cache
    def _build_python_index(
        cls, project_path: str
    ) -> tuple[
        ClassIndexType,
        ClassFuncIndexType,
        FuncIndexType,
        ClassRelationIndexType,
        list[str],
    ]:
        class_index: ClassIndexType = defaultdict(list)
        class_func_index: ClassFuncIndexType = defaultdict(lambda: defaultdict(list))
        function_index: FuncIndexType = defaultdict(list)
        class_relation_index: ClassRelationIndexType = defaultdict(list)

        # TODO: Should be able to ignore directories...
        py_files = find_python_files(project_path)
        # holds the parsable subset of all py files
        parsed_py_files = []
        for py_file in py_files:
            file_info = parse_python_file(py_file)
            if file_info is None:
                # parsing of this file failed
                continue
            parsed_py_files.append(py_file)
            # extract from file info, and form search index
            classes, class_to_funcs, top_level_funcs, class_relation_map = file_info

            # (1) build class index
            for c, start, end in classes:
                class_index[c].append((py_file, LineRange(start, end)))

            # (2) build class-function index
            for c, class_funcs in class_to_funcs.items():
                for f, start, end in class_funcs:
                    class_func_index[c][f].append((py_file, LineRange(start, end)))

            # (3) build (top-level) function index
            for f, start, end in top_level_funcs:
                function_index[f].append((py_file, LineRange(start, end)))

            # (4) build class-superclass index
            for (c, start, end), super_classes in class_relation_map.items():
                class_relation_index[c] = super_classes

        return (
            class_index,
            class_func_index,
            function_index,
            class_relation_index,
            parsed_py_files,
        )

    def _file_line_to_class_and_func(
        self, file_path: str, line_no: int  # noqa
    ) -> tuple[str | None, str | None]:
        """
        Given a file path and a line number, return the class and function name.

        If the line is not inside a class or function, return None.
        """
        # check whether this line is inside a class
        for class_name in self.class_func_index:
            func_dict = self.class_func_index[class_name]
            for func_name, func_info in func_dict.items():
                for file_name, (start, end) in func_info:
                    if file_name == file_path and start <= line_no <= end:
                        return class_name, func_name

        # not in any class; check whether this line is inside a top-level function
        for func_name in self.function_index:
            for file_name, (start, end) in self.function_index[func_name]:
                if file_name == file_path and start <= line_no <= end:
                    return None, func_name

        # this file-line is not recorded in any of the indexes
        return None, None

    def _search_func_in_class(
        self, function_name: str, class_name: str
    ) -> list[SearchResult]:
        """
        Search for the function name in the class.

        Args:
            function_name (str): Name of the function.
            class_name (str): Name of the class.

        Returns:
            The list of code snippets searched.
        """
        result: list[SearchResult] = []
        if class_name not in self.class_func_index:
            return result
        if function_name not in self.class_func_index[class_name]:
            return result
        for fname, (start, end) in self.class_func_index[class_name][function_name]:
            func_code = get_code_snippets(fname, start, end)
            res = SearchResult(fname, start, end, class_name, function_name, func_code)
            result.append(res)
        return result

    def _search_func_in_all_classes(self, function_name: str) -> list[SearchResult]:
        """
        Search for the function name in all classes.

        Args:
            function_name (str): Name of the function.

        Returns:
            The list of code snippets searched.
        """
        result: list[SearchResult] = []
        for class_name in self.class_index:
            res = self._search_func_in_class(function_name, class_name)
            result.extend(res)
        return result

    def _search_top_level_func(self, function_name: str) -> list[SearchResult]:
        """
        Search for top-level function name in the entire project.

        Args:
            function_name (str): Name of the function.

        Returns:
            The list of code snippets searched.
        """
        result: list[SearchResult] = []
        if function_name not in self.function_index:
            return result

        for fname, (start, end) in self.function_index[function_name]:
            func_code = get_code_snippets(fname, start, end)
            res = SearchResult(fname, start, end, None, function_name, func_code)
            result.append(res)
        return result

    def _search_func_in_code_base(self, function_name: str) -> list[SearchResult]:
        """Search for this function, from both top-level and all class definitions."""
        result: list[SearchResult] = []  # list of (file_name, func_code)
        # (1) search in top level
        top_level_res = self._search_top_level_func(function_name)
        class_res = self._search_func_in_all_classes(function_name)
        result.extend(top_level_res)
        result.extend(class_res)
        return result

    def _get_candidate_matched_py_files(self, target_file_name: str):
        """
        Search for files in the project that may match target_file_name.

        Returns:
            - all matched files, in abs path.
        """
        parsed_files_lower = [f.lower() for f in self.parsed_files]
        parsed_files = zip(self.parsed_files, parsed_files_lower)
        target_lower = target_file_name.lower()

        candidates = []
        for orig_file, lower_file in parsed_files:
            if lower_file.endswith(target_lower):
                candidates.append(orig_file)
        return candidates

    # NOTE: SearchResult objects returned by search APIs are not used when
    # communicating with model - they are mainly for our own use cases.
    # Only the first `tool_result` returned value is what sent to the model.

    # not search API - for writing patch
    # if we are searching for only a class when writing patch, likely we do not have
    # enough info the result can be too long, so we just show the first two
    # TODO: what to do with this method? It's not a method exposed to the agent, but
    # maybe we also want to catch exceptions from it?

    @catch_all_and_log
    def get_class_full_snippet(
        self, class_name: str
    ) -> tuple[str, list[SearchResult], bool]:
        search_res: list[SearchResult] = []
        tool_result = f"Could not find class {class_name} in the codebase."

        if class_name not in self.class_index:
            return tool_result, search_res, False

        for fname, (start, end) in self.class_index[class_name]:
            code = get_code_snippets(fname, start, end)
            res = SearchResult(fname, start, end, class_name, None, code)
            search_res.append(res)

        if not search_res:
            return tool_result, search_res, False

        # the good path
        # for all the searched result, append them and form the final result
        tool_result = (
            f"Found {len(search_res)} classes with name {class_name} in the "
            f"codebase:\n\n"
        )

        if len(search_res) > 2:
            tool_result += "Too many results, showing full code for 2 of them:\n"

        final_search_res = search_res[:2]
        for idx, res in enumerate(final_search_res):
            res_str = res.to_tagged_str(self.project_path)
            tool_result += f"- Search result {idx + 1}:\n```\n{res_str}\n```"
        return tool_result, final_search_res, True

    @catch_all_and_log
    def search_class(self, class_name: str) -> tuple[str, list[SearchResult], bool]:
        """Search for a class in the codebase.

        Only the signature of the class is returned. The class signature
        includes class name, base classes, and signatures for all of its
        methods/properties.

        Args:
            class_name (string): Name of the class to search for.
        """
        # initialize them to error case
        search_res: list[SearchResult] = []
        tool_result = f"Could not find class `{class_name}` in the codebase."

        if class_name not in self.class_index:
            return tool_result, search_res, False

        for fname, (start, end) in self.class_index[class_name]:
            # there are some classes; we return their signatures
            code = get_class_signature(fname, class_name)
            res = SearchResult(fname, start, end, class_name, None, code)
            search_res.append(res)

        if not search_res:
            # this should not happen, but just in case
            return tool_result, search_res, False

        # the good path
        # for all the searched result, append them and form the final result
        tool_result = (
            f"Found {len(search_res)} classes with name `{class_name}` in the "
            f"codebase:\n\n"
        )
        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_result += "They appeared in the following files:\n"
            tool_result += SearchResult.collapse_to_file_level(
                search_res, self.project_path
            )
        else:
            for idx, res in enumerate(search_res):
                res_str = res.to_tagged_str(self.project_path)
                tool_result += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        final_search_res = search_res[:RESULT_SHOW_LIMIT]
        return tool_result, final_search_res, True

    @catch_all_and_log
    def search_method(self, method_name: str) -> tuple[str, list[SearchResult], bool]:
        """Search for a method in the entire codebase.

        Returns the actual code of the method.

        Args:
            method_name (string): Name of the method to search for.
        """
        search_res: list[SearchResult] = self._search_func_in_code_base(method_name)
        if not search_res:
            tool_output = f"Could not find method `{method_name}` in the codebase."
            return tool_output, [], False

        tool_output = (
            f"Found {len(search_res)} methods with name `{method_name}` in "
            f"the codebase:\n\n"
        )

        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following files:\n"
            tool_output += SearchResult.collapse_to_file_level(
                search_res, self.project_path
            )
        else:
            for idx, res in enumerate(search_res):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"

        final_search_res = search_res[:RESULT_SHOW_LIMIT]
        return tool_output, final_search_res, True

    @catch_all_and_log
    def search_code(self, code_str: str) -> tuple[str, list[SearchResult], bool]:
        """Search for a code snippet in the entire codebase.

        Returns the method that contains the code snippet, if it is found inside a
        method. Otherwise, returns the region of code surrounding it.

        Args:
            code_str (string): The code snippet to search for.
        """
        # attempt to search for this code string in all py files
        search_res: list[SearchResult] = []
        for file_path in self.parsed_files:
            searched_line_and_code: list[
                tuple[int, str]
            ] = get_code_region_containing_code(file_path, code_str)
            if not searched_line_and_code:
                continue
            for searched in searched_line_and_code:
                line_no, code_region = searched
                # from line_no, check which function and class we are in
                class_name, func_name = self._file_line_to_class_and_func(
                    file_path, line_no
                )
                res = SearchResult(
                    file_path,
                    line_no,
                    line_no,
                    class_name,
                    func_name,
                    code_region,
                )
                search_res.append(res)

        if not search_res:
            tool_output = f"Could not find code `{code_str}` in the codebase."
            return tool_output, [], False

        # good path
        tool_output = (
            f"Found {len(search_res)} snippets containing `{code_str}` in "
            f"the codebase:\n\n"
        )

        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following files:\n"
            tool_output += SearchResult.collapse_to_file_level(
                search_res, self.project_path
            )
        else:
            for idx, res in enumerate(search_res):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"

        final_search_res = search_res[:RESULT_SHOW_LIMIT]
        return tool_output, final_search_res, True

    @catch_all_and_log
    def search_class_in_file(
        self, class_name, file_name: str
    ) -> tuple[str, list[SearchResult], bool]:
        """Search for a class in a given file.

        Returns the actual code of the entire class definition.

        Args:
            class_name (string): Name of the class to search for.
            file_name (string): The file to search in. Must be a valid python file name.
        """
        search_res: list[SearchResult] = []

        # (1) check whether we can get the file
        candidate_py_abs_paths = self._get_candidate_matched_py_files(file_name)
        if not candidate_py_abs_paths:
            tool_output = f"Could not find file `{file_name}` in the codebase."
            return tool_output, search_res, False

        # (2) search for this class in the entire code base (we do filtering later)
        if class_name not in self.class_index:
            tool_output = f"Could not find class `{class_name}` in the codebase."
            return tool_output, search_res, False

        # (3) class is there, check whether it exists in the file specified.
        for fname, (start, end) in self.class_index[class_name]:
            if fname in candidate_py_abs_paths:
                class_code = get_code_snippets(fname, start, end)
                res = SearchResult(fname, start, end, class_name, None, class_code)
                search_res.append(res)

        if not search_res:
            tool_output = f"Could not find class `{class_name}` in file `{file_name}`."
            return tool_output, search_res, False

        # good path; we have result, now just form a response
        tool_output = (
            f"Found {len(search_res)} classes with name `{class_name}` in "
            f"file `{file_name}`:\n\n"
        )
        for idx, res in enumerate(search_res):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, search_res, True

    @catch_all_and_log
    def search_method_in_file(
        self, method_name: str, file_name: str
    ) -> tuple[str, list[SearchResult], bool]:
        """Search for a method in a given file.

        Returns the actual code of the method.

        Args:
            method_name (string): Name of the method to search for.
            file_name (string): The file to search in. Must be a valid python file name.
        """
        # (1) check whether we can get the file
        # supports both when file_name is relative to project root, and when
        # it is just a short name
        candidate_py_abs_paths = self._get_candidate_matched_py_files(file_name)
        # print(candidate_py_files)
        if not candidate_py_abs_paths:
            tool_output = f"Could not find file `{file_name}` in the codebase."
            return tool_output, [], False

        # (2) search for this method in the entire code base (we do filtering later)
        search_res: list[SearchResult] = self._search_func_in_code_base(method_name)
        if not search_res:
            tool_output = f"The method `{method_name}` does not appear in the codebase."
            return tool_output, [], False

        # (3) filter the search result => they need to be in one of the files!
        filtered_res: list[SearchResult] = [
            res for res in search_res if res.file_path in candidate_py_abs_paths
        ]

        # (4) done with search, now prepare result
        if not filtered_res:
            tool_output = (
                f"There is no method with name `{method_name}` in file `{file_name}`."
            )
            return tool_output, [], False

        tool_output = (
            f"Found {len(filtered_res)} methods with name `{method_name}` in "
            f"file `{file_name}`:\n\n"
        )

        # when searching for a method in one file, it's rare that there are
        # many candidates, so we do not trim the result
        for idx, res in enumerate(filtered_res):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, filtered_res, True

    @catch_all_and_log
    def search_method_in_class(
        self, method_name: str, class_name: str
    ) -> tuple[str, list[SearchResult], bool]:
        """Search for a method in a given class.

        Returns the actual code of the method.

        Args:
            method_name (string): Name of the method to search for.
            class_name (string): Consider only methods in this class.
        """
        if class_name not in self.class_index:
            tool_output = f"Could not find class `{class_name}` in the codebase."
            return tool_output, [], False

        # has this class, check its methods
        search_res: list[SearchResult] = self._search_func_in_class(
            method_name, class_name
        )
        if not search_res:
            tool_output = (
                f"Could not find method `{method_name}` in class `{class_name}`."
            )
            return tool_output, [], False

        # found some methods, prepare the result
        tool_output = (
            f"Found {len(search_res)} methods with name `{method_name}` in "
            f"class `{class_name}`:\n\n"
        )

        # There can be multiple classes defined in multiple files, which contain the
        # same method still trim the result, just in case
        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_output += (
                f"Too many results, showing full code for "
                f"{RESULT_SHOW_LIMIT} of them, and the rest just file names:\n"
            )
        first_five = search_res[:RESULT_SHOW_LIMIT]
        for idx, res in enumerate(first_five):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        # for the rest, collect the file names into a set
        if rest := search_res[RESULT_SHOW_LIMIT:]:
            tool_output += "Other results are in these files:\n"
            tool_output += SearchResult.collapse_to_file_level(rest, self.project_path)

        return tool_output, first_five, True

    @catch_all_and_log
    def search_code_in_file(
        self, code_str: str, file_name: str
    ) -> tuple[str, list[SearchResult], bool]:
        """Search for a code snippet in a given file.

        Returns the entire method that contains the code snippet.

        Args:
            code_str (string): The code snippet to search for.
            file_name (string): The file to search in. Must be a valid python file name
            in the project.
        """
        code_str = code_str.removesuffix(")")

        candidate_py_files = [f for f in self.parsed_files if f.endswith(file_name)]
        if not candidate_py_files:
            tool_output = f"Could not find file `{file_name}` in the codebase."
            return tool_output, [], False

        # start searching for code in the filtered files
        search_res: list[SearchResult] = []
        for file_path in candidate_py_files:
            searched_line_and_code: list[
                tuple[int, str]
            ] = get_code_region_containing_code(file_path, code_str)
            if not searched_line_and_code:
                continue
            for searched in searched_line_and_code:
                line_no, code_region = searched
                # from line_no, check which function and class we are in
                class_name, func_name = self._file_line_to_class_and_func(
                    file_path, line_no
                )
                res = SearchResult(
                    file_path,
                    line_no,
                    line_no,
                    class_name,
                    func_name,
                    code_region,
                )
                search_res.append(res)

        if not search_res:
            tool_output = f"Could not find code `{code_str}` in file `{file_name}`."
            return tool_output, [], False

        # good path
        # There can be a lot of results, from multiple files.
        tool_output = (
            f"Found {len(search_res)} snippets with code `{code_str}` in file "
            f"`{file_name}`:\n\n"
        )
        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following methods:\n"
            tool_output += SearchResult.collapse_to_method_level(
                search_res, self.project_path
            )
        else:
            for idx, res in enumerate(search_res):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"

        final_search_res = search_res[:RESULT_SHOW_LIMIT]
        return tool_output, final_search_res, True

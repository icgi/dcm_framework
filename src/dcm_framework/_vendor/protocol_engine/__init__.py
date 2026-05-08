"""

Protocol Engine

"""

__version__ = "0.1.0"


import concurrent.futures
import datetime
import graphlib
import logging
import pathlib
import random
import secrets
import socket
import subprocess
import sys
import types

import friendly_names
import numpy
import pandas
import tqdm
import yaspin
import yaspin.spinners


logger = logging.getLogger(__name__)

def contract(provides=None, requires=None, level="frame", interactive=False):
    """

        Stamps contract metadata onto a transformer's ``__call__`` so the engine can plan
        execution order and dispatch correctly. ``provides`` and ``requires`` are lists of
        protocol column keys; ``level`` is ``"frame"`` (default; called once per protocol
        with ``(protocol, manifest)`` and returning ``(protocol, manifest)``) or ``"entry"``
        (called per row with ``(entry, manifest)`` and returning a dict or ``pandas.Series``
        of new column values for that row). ``interactive`` marks transformers that require
        stdin (e.g. user prompts) and should not be wrapped in a spinner. All runtime
        enforcement lives in ``Protocol.apply``; this decorator only attaches attributes.

    """

    def decorator(method):
        method.provides = provides or []
        method.requires = requires or []
        method.level = level
        method.interactive = interactive
        return method

    return decorator


class Protocol:
    """

        Base class for protocol assembly. Resolves execution order from contract metadata,
        creates a workspace directory, seeds the python and numpy random number generators,
        and records trial identity, execution environment, and git metadata into the manifest.

        Override ``random_seed`` to change the seed.

    """

    random_seed = 42

    def __init__(self, workspace=None):
        """ Resolves the workspace directory and ensures it exists on disk. """

        if workspace is None:
            workspace = self._generate_workspace_directory()
        self.workspace = pathlib.Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _generate_workspace_directory(self):
        """

            Builds the default ``experiment___<friendly>-<nnn>___<date>`` workspace path.

        """

        friendly = friendly_names.generate(words=3, separator="-")
        suffix = secrets.randbelow(1000)
        date_token = datetime.date.today().isoformat()
        name = f"experiment___{friendly}-{suffix:03d}___{date_token}"
        result = pathlib.Path(name)
        return result

    def log(self, message, level=logging.INFO, echo=True):
        """

            Routes a message through the module logger, appends it to ``workspace/log.txt``,
            and (when ``echo`` is true) prints it to stdout via ``tqdm.write``. Pass ``echo=False``
            for file-only entries when a spinner or other stdout owner is active.

        """

        logger.log(level, message)
        log_path = self.workspace / "log.txt"
        timestamp = datetime.datetime.now().isoformat(timespec="seconds")
        level_name = logging.getLevelName(level)
        line = f"{timestamp} {level_name} {message}\n"
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(line)
        if echo:
            tqdm.tqdm.write(line.rstrip())

    def _collect_transformers(self):
        """

            Collects mixin base classes whose __call__ carries a contract decorator.

        """
        # walk the MRO and keep only mixin bases whose __call__ was decorated with @contract
        result = [
            base for base in type(self).__mro__
            if base not in (type(self), Protocol, object)
            and hasattr(getattr(base, "__call__", None), "provides")
        ]
        return result

    def _resolve_execution_order(self, transformer_classes):
        """

            Topological sort of transformer classes. Uses MRO position as tiebreaker for unconstrained nodes.

        """

        result = None

        # MRO index used as a stable tiebreaker when no contract edge exists between two transformers
        mro_position = {
            transformer_class: index
            for index, transformer_class in enumerate(transformer_classes)
        }

        # reverse map: column name -> the transformer class that provides it
        provider_index = {}
        for transformer_class in transformer_classes:
            call_method = transformer_class.__call__
            for column in call_method.provides:
                provider_index[column] = transformer_class

        # build the dependency graph: each transformer depends on the providers of its required columns
        dependencies = {}
        for transformer_class in transformer_classes:
            call_method = transformer_class.__call__
            dependencies[transformer_class] = {
                provider_index[column]
                for column in call_method.requires
                if column in provider_index
            }

        # chains unconstrained transformers to their MRO predecessor
        sorted_by_mro = sorted(transformer_classes, key=lambda transformer_class: mro_position[transformer_class])
        for index, transformer_class in enumerate(sorted_by_mro):
            if index == 0:
                continue
            call_method = transformer_class.__call__
            has_contract_edges = call_method.requires or call_method.provides
            if not has_contract_edges:
                predecessor = sorted_by_mro[index - 1]
                dependencies[transformer_class].add(predecessor)

        # topological sort yields a linear execution order consistent with the dependency graph
        sorter = graphlib.TopologicalSorter(dependencies)
        result = list(sorter.static_order())
        return result


    #
    #    CALLBACKS
    #

    def before_transformation(self, ordinal, transformer_class, protocol, manifest):
        result = protocol, manifest
        return result

    def after_transformation(self, ordinal, transformer_class, protocol, manifest):
        result = protocol, manifest
        return result


    def before_protocol_execution(self, protocol, manifest):
        """

            Seeds the random number generators and stamps trial, environment, and git metadata.

        """

        self._seed_random(manifest)
        self._record_provenance(manifest)

        result = protocol, manifest
        return result

    def after_protocol_execution(self, protocol, manifest):
        result = protocol, manifest
        return result

    def on_transformer_error(self, ordinal, transformer_class, protocol, manifest, exception):
        """

            Default handler logs the failure and re-raises. Override to capture diagnostics or recover.

        """

        self.log(
            f"transformer {transformer_class.__name__} Step #{ordinal} raised "
            f"{type(exception).__name__}: {exception}",
            level=logging.ERROR,
        )
        raise exception


    #
    #    MANIFEST HELPERS
    #


    def _seed_random(self, manifest):
        """

            Seeds python and numpy global RNGs and records the seed in the manifest.

        """

        random.seed(self.random_seed)
        numpy.random.seed(self.random_seed)
        manifest[("parameters", "random_seed")] = self.random_seed

    def _record_provenance(self, manifest):
        """

            Stamps trial identity, environment, and git metadata into the manifest.

        """

        manifest[("trial", "identifier")] = self.workspace.name
        manifest[("trial", "started_at")] = datetime.datetime.now().isoformat(timespec="seconds")
        manifest[("trial", "workspace")] = str(self.workspace)
        manifest[("environment", "host")] = socket.gethostname()
        manifest[("environment", "python_version")] = sys.version.split()[0]
        manifest[("environment", "platform")] = sys.platform
        manifest[("git", "sha")] = self._read_git_sha()
        manifest[("git", "dirty")] = self._read_git_dirty()
        manifest[("git", "branch")] = self._read_git_branch()

    def _read_git_sha(self):
        """

            Returns the current commit sha or an empty string if git is unavailable.

        """

        result = ""
        try:
            completed = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, check=False, cwd=str(pathlib.Path.cwd()),
            )
            if completed.returncode == 0:
                result = completed.stdout.strip()
        except FileNotFoundError:
            pass
        return result

    def _read_git_dirty(self):
        """

            Returns True when the working tree has uncommitted changes.

        """

        result = False
        try:
            completed = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, check=False, cwd=str(pathlib.Path.cwd()),
            )
            if completed.returncode == 0:
                result = bool(completed.stdout.strip())
        except FileNotFoundError:
            pass
        return result

    def _read_git_branch(self):
        """

            Returns the current branch name or an empty string if git is unavailable.

        """

        result = ""
        try:
            completed = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, check=False, cwd=str(pathlib.Path.cwd()),
            )
            if completed.returncode == 0:
                result = completed.stdout.strip()
        except FileNotFoundError:
            pass
        return result


    #
    #    EXECUTION
    #

    def build(self, initial_frame=None, manifest=None):
        """

            Executes all contract-decorated transformers in dependency order.

        """

        # seed the pipeline state: an empty frame and empty manifest unless caller supplied them
        protocol = initial_frame if initial_frame is not None else pandas.DataFrame()
        manifest = manifest if manifest is not None else {}

        # discover participating transformers and the order in which to run them
        transformer_classes = self._collect_transformers()
        execution_order = self._resolve_execution_order(transformer_classes)

        protocol, manifest = self.before_protocol_execution(protocol, manifest)

        # execute the participating transformers while propagating protocols and manifests
        total = len(execution_order)
        for ordinal, transformer_class in enumerate(execution_order, start=1):
            protocol, manifest = self.run_transformer(ordinal, total, transformer_class, protocol, manifest)

        protocol, manifest = self.after_protocol_execution(protocol, manifest)

        result = protocol, manifest
        return result

    def run_transformer(self, ordinal, total, transformer_class, protocol, manifest):
        """

            Executes a single transformer surrounded by ``before_transformation`` and
            ``after_transformation`` callbacks. Renders a one-line spinner of the form
            ``T* #N/M: Name (K protocol columns)`` while the transformer runs, finalized
            with [OK] on success or [FAIL] on failure. When the transformer's contract
            sets ``interactive=True``, the spinner is suppressed to avoid conflicts with
            stdin-based prompts. The transformer's ``__call__`` is bound to ``self`` and
            handed to ``Protocol.apply`` for dispatch. Subclasses can override and delegate
            via ``super().run_transformer(...)``.

        """

        is_interactive = getattr(transformer_class.__call__, "interactive", False)

        if is_interactive:
            result = self._run_transformer_without_spinner(ordinal, total, transformer_class, protocol, manifest)
        else:
            result = self._run_transformer_with_spinner(ordinal, total, transformer_class, protocol, manifest)

        return result

    def _run_transformer_with_spinner(self, ordinal, total, transformer_class, protocol, manifest):
        """ Executes a transformer with a yaspin spinner around it. """

        name = transformer_class.__name__
        running_text = f"Applying T* #{ordinal}/{total}: {name}"
        bound_call = transformer_class.__call__.__get__(self)
        failed = False

        spinner_style = yaspin.spinners.Spinners.line

        with yaspin.yaspin(spinner_style, text=running_text, color="cyan") as spinner:
            protocol, manifest = self.before_transformation(ordinal, transformer_class, protocol, manifest)

            try:
                protocol, manifest = self.apply(bound_call, protocol, manifest)
            except Exception as exception:
                failed = True
                spinner.fail("[FAIL]")
                protocol, manifest = self.on_transformer_error(
                    ordinal, transformer_class, protocol, manifest, exception,
                )

            protocol, manifest = self.after_transformation(ordinal, transformer_class, protocol, manifest)
            column_count = len(protocol.columns)
            final_text = f"T* {ordinal}/{total}: {name} ({column_count} protocol columns)"
            spinner.text = final_text

            if not failed:
                spinner.ok("[OK]")

        self.log(final_text, echo=False)

        result = protocol, manifest
        return result

    def _run_transformer_without_spinner(self, ordinal, total, transformer_class, protocol, manifest):
        """ Executes an interactive transformer without a spinner. """

        name = transformer_class.__name__
        bound_call = transformer_class.__call__.__get__(self)

        protocol, manifest = self.before_transformation(ordinal, transformer_class, protocol, manifest)

        try:
            protocol, manifest = self.apply(bound_call, protocol, manifest)
        except Exception as exception:
            protocol, manifest = self.on_transformer_error(
                ordinal, transformer_class, protocol, manifest, exception,
            )

        protocol, manifest = self.after_transformation(ordinal, transformer_class, protocol, manifest)

        column_count = len(protocol.columns)
        final_text = f"T* {ordinal}/{total}: {name} ({column_count} protocol columns)"
        self.log(final_text)

        result = protocol, manifest
        return result

    def apply(
        self, callable_, protocol, manifest,
        mode=None, use_concurrency=True,
        max_workers=None, executor_type="thread",
        shuffle=False,
    ):
        """

            Single dispatch fork for the engine. Validates required columns once, then
            either invokes ``callable_`` once at frame scope or dispatches it per row and
            joins the results back onto the protocol. Returns ``(protocol, manifest)`` in
            both modes so the caller does not need to know which path ran.

            ``mode`` defaults to the callable's declared ``level`` attribute (set by
            ``@contract``); pass ``"frame"`` or ``"entry"`` explicitly for plain callables.

            Frame mode invokes ``callable_(protocol, manifest)`` once and expects
            ``(protocol, manifest)`` back; the manifest stays mutable so frame-level steps
            can record per-step metadata.

            Entry mode invokes ``callable_(entry, frozen_manifest)`` for every row and
            expects a dict or ``pandas.Series`` of new column values per row. The manifest
            is exposed as a ``MappingProxyType`` (thread executor) or copied ``dict``
            (process executor) so per-row writes cannot leak across rows. Results are
            reindexed to the input order and joined onto the protocol by index.

            ``use_concurrency=True`` runs per-row calls in an executor; ``executor_type``
            selects ``"thread"`` (default, cheap) or ``"process"`` (true parallelism but
            the callable, entry, and manifest must be picklable). ``max_workers`` overrides
            the executor default. ``shuffle=True`` randomizes submission order, useful when
            row latency is uneven; the result is always reindexed to the input frame's
            index. ``use_concurrency=False`` calls each row inline for cleaner tracebacks.
            Per-row exceptions are wrapped with the failing row's index value.

        """

        if mode is None:
            mode = getattr(callable_, "level", "frame")

        # column-requirement guard runs once for both modes
        missing = [
            column for column in getattr(callable_, "requires", [])
            if column not in protocol.columns
        ]
        if missing:
            raise KeyError(f"transformer requires missing columns: {missing}")

        if mode == "frame":
            protocol, manifest = callable_(protocol, manifest)
        elif mode == "entry":
            # process pool subprocesses cannot share a MappingProxyType (it does not pickle);
            # they pickle a copy of the manifest dict, which provides equivalent isolation
            if executor_type == "process":
                frozen_manifest = dict(manifest)
            else:
                frozen_manifest = types.MappingProxyType(manifest)

            if shuffle:
                iteration_frame = protocol.sample(frac=1)
            else:
                iteration_frame = protocol

            # collect (index, row_result) pairs in one list; the concurrent branch needs a
            # separate submission pass so the executor can run rows in parallel before any
            # results are awaited, but the assembly downstream is a single iteration
            if use_concurrency:
                executor_class = {
                    "thread": concurrent.futures.ThreadPoolExecutor,
                    "process": concurrent.futures.ProcessPoolExecutor,
                }[executor_type]
                with executor_class(max_workers=max_workers) as executor:
                    pairs_for_pending = [
                        (entry.name, executor.submit(callable_, entry, frozen_manifest))
                        for _, entry in iteration_frame.iterrows()
                    ]
                    pairs_for_results = []
                    for index_value, future in pairs_for_pending:
                        try:
                            pairs_for_results.append((index_value, future.result()))
                        except Exception as exception:
                            raise RuntimeError(
                                f"row {index_value!r} raised {type(exception).__name__}: {exception}"
                            ) from exception
            else:
                pairs_for_results = []
                for _, entry in iteration_frame.iterrows():
                    try:
                        pairs_for_results.append((entry.name, callable_(entry, frozen_manifest)))
                    except Exception as exception:
                        raise RuntimeError(
                            f"row {entry.name!r} raised {type(exception).__name__}: {exception}"
                        ) from exception

            buffer_for_indices = [index_value for index_value, _ in pairs_for_results]
            buffer_for_records = [row_result for _, row_result in pairs_for_results]
            frame_with_results = pandas.DataFrame(buffer_for_records, index=buffer_for_indices)

            # tuple-keyed columns are promoted to MultiIndex so the join respects the convention
            has_columns = len(frame_with_results.columns) > 0
            tuple_columns = has_columns and all(
                isinstance(column, tuple) for column in frame_with_results.columns
            )
            if tuple_columns:
                frame_with_results.columns = pandas.MultiIndex.from_tuples(
                    list(frame_with_results.columns)
                )

            # restore original order so the index-aligned join is stable under shuffle
            frame_with_results = frame_with_results.reindex(protocol.index)
            protocol = protocol.join(frame_with_results, how="left", validate="one_to_one")
        else:
            raise ValueError(f"unknown mode: {mode!r} (expected 'frame' or 'entry')")

        result = protocol, manifest
        return result



